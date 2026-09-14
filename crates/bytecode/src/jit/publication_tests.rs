//! Own-thread publication controls; synthetic code never reads guest pointers.
use super::*;

fn branch_word(at: usize, target: usize) -> u32 {
    0x14000000 | branch_displacement(at, target, 26, CodegenLimit::Jump).unwrap()
}

fn result(code: &platform::Code, offset: usize) -> usize {
    // SAFETY: this fixture contains only checked direct branches, mov x0 and
    // ret. It accesses no supplied pointers and preserves the host ABI.
    let output = unsafe { code.abi_probe(offset, [0; 8]) };
    assert_eq!(output[1], 0x1357);
    assert_eq!(output[2], output[3]);
    output[0]
}

#[test]
fn checked_append_and_patch_publishes_new_targets_with_stable_old_entries() {
    let mut code = platform::Code::reserve(4096).unwrap();
    code.append(&[branch_word(0, 2), branch_word(1, 2), 0xd2800020, 0xd65f03c0]).unwrap();
    let base = code.published().0;
    assert_eq!((result(&code, 0), result(&code, 4)), (1, 1));
    let mut target = 2;
    for value in 2..66u32 {
        let before = code.published().1.to_vec();
        let next = before.len() / 4;
        let patches = [CodePatch { offset: 0, expected: branch_word(0, target), word: branch_word(0, next) },
            CodePatch { offset: 4, expected: branch_word(1, target), word: branch_word(1, next) }];
        let offset = code.append_and_patch(&[0xd2800000 | (value << 5), 0xd65f03c0], &patches).unwrap();
        assert_eq!(offset, before.len());
        assert_eq!(code.published().0, base);
        assert_eq!(&code.published().1[8..offset], &before[8..]);
        assert_eq!((result(&code, 0), result(&code, 4)), (value as usize, value as usize));
        target = next;
    }
}

#[test]
fn branch_only_transactions_support_backward_targets_and_leave_size_unchanged() {
    let mut code = platform::Code::reserve(64).unwrap();
    code.append(&[0xd2800120, 0xd65f03c0, branch_word(2, 0)]).unwrap(); // return 9
    assert_eq!(result(&code, 8), 9);
    let forward = CodePatch { offset: 8, expected: branch_word(2, 0), word: branch_word(2, 3) };
    assert_eq!(code.append_and_patch(&[0xd2800140, 0xd65f03c0], &[forward]).unwrap(), 12); // return 10
    assert_eq!(result(&code, 8), 10);
    let before = code.published().1.to_vec();
    assert_eq!(code.append_and_patch(&[], &[CodePatch { offset: 8, expected: forward.word, word: forward.expected }]).unwrap(), before.len());
    assert_eq!(code.published().1.len(), before.len());
    assert_eq!(result(&code, 8), 9);
}

#[test]
fn rejected_patch_batches_never_append_or_change_an_earlier_valid_branch() {
    let mut code = platform::Code::reserve(64).unwrap();
    code.append(&[branch_word(0, 2), branch_word(1, 2), 0xd2800020, 0xd65f03c0]).unwrap();
    let good = CodePatch { offset: 0, expected: branch_word(0, 2), word: branch_word(0, 4) };
    let second = CodePatch { offset: 4, expected: branch_word(1, 2), word: branch_word(1, 4) };
    let invalid = [
        vec![CodePatch { offset: 1, ..good }],
        vec![CodePatch { offset: 16, ..good }],
        vec![CodePatch { offset: usize::MAX, ..good }],
        vec![CodePatch { expected: 0xd65f03c0, ..good }],
        vec![CodePatch { expected: branch_word(0, 3), ..good }],
        vec![CodePatch { word: 0xd65f03c0, ..good }],
        vec![CodePatch { word: 0x17ffffff, ..good }], // negative target before arena
        vec![CodePatch { word: branch_word(0, 6), ..good }], // one-past transaction
        vec![good, good],
        vec![second, good],
        vec![good, CodePatch { expected: branch_word(1, 3), ..second }],
    ];
    let before = code.published().1.to_vec();
    for patches in invalid {
        assert!(code.append_and_patch(&[0xd2800040, 0xd65f03c0], &patches).is_err());
        assert_eq!(code.published().1, before);
        assert_eq!((result(&code, 0), result(&code, 4)), (1, 1));
    }
    assert!(code.append_and_patch(&[], &[good]).is_err());
    assert!(code.append_and_patch(&[0xd65f03c0; 13], &[good]).is_err());
    assert_eq!(code.published().1, before);
    assert_eq!((result(&code, 0), result(&code, 4)), (1, 1));
}
