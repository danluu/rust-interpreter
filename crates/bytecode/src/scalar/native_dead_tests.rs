use super::*;
const ZERO10: u32 = 0xaa1f03ea;
const OK: u32 = 0xaa1f03e0;
const FAIL: u32 = 0xd2800020;
const RET: u32 = 0xd65f03c0;

#[test]
fn native_scalar_dead_registers_keep_flags_memory_and_vector_operands() {
    let before = [0xaa1f03eb, 0xaa1f03ec, 0x9a8c116a, 0xf9000049, OK, RET];
    assert_eq!(eliminate(&before).unwrap(), before[3..]);
    let before = [0xd2800029, 0xf2a00049, 0xf9000049, ZERO10, OK, RET];
    assert_eq!(eliminate(&before).unwrap(), [before[0], before[1], before[2], OK, RET]);
    let before = [0xd10043ff, 0xf94003ea, 0xf90007ea, 0x910043ff, OK, RET];
    assert_eq!(eliminate(&before).unwrap(), before);
    let before = [0x9e670120, 0x0e205800, 0x0e31b800, 0x0e013c09, 0xf9000049, OK, RET];
    assert_eq!(eliminate(&before).unwrap(), before);
    assert_eq!(eliminate(&[before[0], before[1], before[2], before[3], OK, RET]).unwrap(), [OK, RET]);
    assert_eq!(decode(0xeb0a013f, 0, 2).unwrap().writes, FLAGS);
    // Two incoming definitions must both survive the merge before a store.
    let before = [0x54000060, ZERO10, 0x14000002, 0xd280002a, 0xf900044a, OK, RET];
    assert_eq!(eliminate(&before).unwrap(), before);
}

#[test]
fn native_scalar_dead_registers_relocate_and_decline_unknown_or_cyclic_code() {
    let before = [0xeb0a013f, 0x54000040, ZERO10, OK, RET];
    assert_eq!(eliminate(&before).unwrap(), [before[0], 0x54000020, OK, RET]);
    // A backward branch targets a removed definition and must land on its next
    // retained instruction. Physical code order differs from execution order.
    let before = [0x14000004, ZERO10, OK, RET, 0x17fffffd];
    assert_eq!(eliminate(&before).unwrap(), [0x14000003, OK, RET, 0x17fffffe]);
    let before = [0x54000080, ZERO10, OK, RET, FAIL, RET];
    assert_eq!(eliminate(&before).unwrap(), [0x54000060, OK, RET, FAIL, RET]);
    let trap = [0xeb1f03ff, 0x54000040, 0x17fffffe, FAIL, RET];
    assert_eq!(eliminate(&trap).unwrap(), trap);
    assert!(eliminate(&[0x14000002, 0xeb1f03ff, 0x54000040, 0x17ffffff, FAIL, RET]).is_err());
    for words in [vec![], vec![0, OK, RET], vec![0x14000006, OK, RET],
                  vec![0x14000000, OK, RET], vec![ZERO10; MAX_WORDS + 1]] {
        assert!(eliminate(&words).is_err());
    }
}

#[test]
#[ignore = "Requires source-qualified saved scalar body/independent compacted-word pairs"]
fn observe_saved_scalar_dead_register_words() {
    let path = std::env::var("SCALAR_DEAD_WORD_FIXTURES").unwrap();
    let input = std::fs::read_to_string(path).unwrap(); assert!(input.len() < 8 * 1024 * 1024);
    let mut count = 0;
    for line in input.lines() {
        let (before, after) = line.split_once('\t').unwrap();
        let parse = |s: &str| s.split_whitespace().map(|w| u32::from_str_radix(w, 16).unwrap()).collect::<Vec<_>>();
        let before = parse(before); let after = parse(after);
        assert_eq!(eliminate(&before).unwrap(), after, "saved scalar body {count}");
        count += 1;
    }
    assert!(count > 50 && count < 200);
    println!("{count} exact saved bodies match the independent compacted-word reference");
}
