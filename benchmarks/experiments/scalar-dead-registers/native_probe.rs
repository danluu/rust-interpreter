//! Isolated std-only live qualification of the saved confined scalar bodies.
#![allow(dead_code)]
const MAX_CODE_BYTES: usize = 262_144;
#[repr(C)]
struct Cursor { remaining: u64, profile_hits: *mut u64 }
#[path = "../../../crates/bytecode/src/scalar/native_dead.rs"]
mod dead;
#[path = "../../../crates/bytecode/src/scalar/native_memory.rs"]
mod publisher;

#[repr(C)]
#[derive(Clone, Debug, PartialEq, Eq)]
struct Output { value: u128, steps: u64, visited: [u64; 8] }

#[test]
fn native_scalar_dead_registers_execute_saved_bodies_with_complete_private_output_and_abi() {
    assert_eq!(std::mem::size_of::<Output>(), 96);
    let text = std::fs::read_to_string(std::env::var("SCALAR_DEAD_WORD_FIXTURES").unwrap()).unwrap();
    assert!(text.len() < 8 * 1024 * 1024);
    let mut arena = publisher::memory::Code::reserve(MAX_CODE_BYTES).unwrap();
    let mut entries = vec![];
    for line in text.lines() {
        let (before, after) = line.split_once('\t').unwrap();
        let parse = |s: &str| s.split_whitespace().map(|w| u32::from_str_radix(w, 16).unwrap()).collect::<Vec<_>>();
        let before = parse(before); let after = parse(after);
        assert_eq!(dead::eliminate(&before).unwrap(), after);
        // Source-qualified scalar bodies access only their input array, private
        // Output and bounded stack. Never dereference a synthesized guest value.
        for &word in &before {
            if matches!(word & 0xffc00000, 0xf9000000 | 0xf9400000) {
                let base = (word >> 5) & 31; let offset = ((word >> 10) & 4095) as usize * 8;
                match base {
                    0 => { assert_eq!(word & 0xffc00000, 0xf9400000); assert!(offset + 8 <= 64 * 16); }
                    2 => assert!(offset + 8 <= std::mem::size_of::<Output>()),
                    31 => assert!(offset + 8 <= 32752),
                    _ => panic!("unexpected scalar memory base {base}"),
                }
            }
        }
        entries.push((arena.append(&before).unwrap(), arena.append(&after).unwrap()));
    }
    assert_eq!(entries.len(), 137);
    let mut state = 0x8e3479253a10u64;
    let mut attempts = 0;
    for (index, &(before, after)) in entries.iter().enumerate() {
        for trial in 0..128 {
            let mut arguments = [0u128; 64];
            for (argument, value) in arguments.iter_mut().enumerate() {
                state ^= state << 13; state ^= state >> 7; state ^= state << 17;
                let edge = [0, 1, u64::MAX as u128, u128::MAX, 1 << 63, 1 << 127,
                    0xaaaaaaaaaaaaaaaa_aaaaaaaaaaaaaaaa, 0x5555555555555555_5555555555555555];
                *value = if trial < 16 { edge[(trial + argument) % edge.len()] }
                    else { (u128::from(state) << 64) | u128::from(state.rotate_left(29)) };
            }
            let snapshots = [before, after].map(|offset| {
                let mut output = Output { value: u128::MAX, steps: u64::MAX, visited: [u64::MAX; 8] };
                let base = [16usize, 4096, 1usize << 40][trial % 3];
                let args = [arguments.as_mut_ptr() as usize, base, std::ptr::from_mut(&mut output) as usize,
                    usize::MAX / 2, 0x1234, 0x5678, 0x9abc, 0];
                // Exact qualified confined code, retained by this arena; all
                // possible native loads/stores are covered by the live arrays.
                let abi = unsafe { arena.tree_abi_probe(offset, args) };
                assert!(abi[0] <= 1);
                assert_eq!([abi[1], abi[2], abi[3], abi[4], abi[7], abi[8], abi[9], abi[10], abi[11], abi[12]],
                    [0x1357, 0x2468, 0x3579, 0x468a, 0x579b, 0x68ac, 0x79bd, 0x8ace, 0x9bdf, 0xace0]);
                assert_eq!(abi[5], abi[6]);
                (abi[0], output)
            });
            assert_eq!(snapshots[0], snapshots[1], "body {index} trial {trial}");
            attempts += 2;
        }
    }
    assert_eq!(attempts, 35072);
    println!("35072 synthetic native body attempts preserve complete private outputs and ABI");
}
