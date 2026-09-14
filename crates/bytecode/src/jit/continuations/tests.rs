use super::*;
use crate::Slot;

fn fixture(tail: Vec<Op>) -> Program {
    let f = |code| Function { name: "continuation fixture".into(), frame_size: 32,
        frame_align: 16, registers: 4, args: vec![], result: Slot { offset: 0, size: 0 }, code };
    let mut code = vec![Op::Local { dst: 0, offset: 0 },
        Op::Call { function: 1, args: vec![], destination: 0 }];
    code.extend(tail);
    Program { version: crate::VERSION, target: "aarch64-apple-darwin".into(), entry: 0,
        data: vec![0; 16], statics: vec![], thread_locals: vec![],
        functions: vec![f(code), f(vec![Op::Return])] }
}

#[test]
fn relocation_uses_byte_offsets_exact_resume_entries_and_missing_target_sentinel() {
    for tail in [vec![Op::Return], vec![Op::Unary { dst: 1, src: 0, bits: 128,
        op: Unary::CountOnes }, Op::Return], vec![]] {
        let native = matches!(tail.first(), Some(Op::Return));
        let p = fixture(tail); crate::validate(&p).unwrap();
        for profiled in [false, true] { for persistent in [false, true] {
            let jit = Jit::new_resumable(&p, profiled, MAX_CODE_BYTES, persistent).unwrap();
            for base in [0, 4, 65532, 65536, 8 * 1024 * 1024] {
                let mut staged = jit.emit_function(&p.functions[0], MAX_CODE_BYTES / 4).unwrap().unwrap();
                assert_eq!(staged.continuations.len(), 1);
                let (at, pc) = staged.continuations[0]; assert_eq!(pc, 2);
                let target = staged.resumes[pc]; assert_eq!(target.is_some(), native);
                let before = staged.words.clone();
                staged.relocate_continuations(base).unwrap();
                let decoded = ((staged.words[at] >> 5) & 0xffff)
                    | (((staged.words[at + 1] >> 5) & 0xffff) << 16);
                assert_eq!(decoded as usize, target.map_or(0, |word| base + 4 * word));
                assert_eq!(&staged.words[..at], &before[..at]);
                assert_eq!(&staged.words[at + 2..], &before[at + 2..]);
            }
            assert!(jit.code.is_none()); assert_eq!(jit.bytes, 0);
        }}
    }
}

#[test]
fn malformed_relocations_reject_before_any_word_is_changed() {
    let p = fixture(vec![Op::Call { function: 1, args: vec![], destination: 0 }, Op::Return]);
    let jit = Jit::new_resumable(&p, false, MAX_CODE_BYTES, true).unwrap();
    for case in 0..8 {
        let mut a = jit.emit_function(&p.functions[0], MAX_CODE_BYTES / 4).unwrap().unwrap();
        assert_eq!(a.continuations.len(), 2);
        let mut base = 65536;
        match case {
            0 => base = 3,
            1 => base = MAX_CODE_BYTES,
            2 => a.continuations[1].0 = a.words.len(),
            3 => a.continuations[1].0 = a.continuations[0].0,
            4 => a.continuations[1].1 = a.resumes.len(),
            5 => a.resumes[a.continuations[1].1] = Some(a.words.len()),
            6 => a.words[a.continuations[1].0 + 1] ^= 1,
            7 => { base = 0; a.resumes[a.continuations[1].1] = Some(0); },
            _ => unreachable!(),
        }
        let before = a.words.clone();
        assert!(a.relocate_continuations(base).is_err(), "case {case}");
        assert_eq!(a.words, before);
    }
    assert!(jit.code.is_none());
}

// Only an independent host assembler supplies these expected words. This
// object is data, never linked or executed; production emission stays custom.
#[test]
fn snapshot_and_continuation_words_match_independent_host_assembler() {
    let dir = std::env::temp_dir().join(format!("rust-interp-continuation-oracle-{}", std::process::id()));
    std::fs::create_dir(&dir).unwrap();
    let mut source = String::from(".text\n");
    let mut actual = vec![];
    for size in [128, 144, 256, 304, 384] {
        let mut a = Assembler::default(); a.abi_copy(size).unwrap();
        actual.extend(a.words);
        for (operation, base) in [("ldr", 11), ("str", 12)] {
            for chunk in 0..size / 16 {
                let vector = if chunk < 8 { chunk } else { chunk + 8 };
                source.push_str(&format!("{operation} q{vector}, [x{base}, #{}]\n", chunk * 16));
            }
        }
    }
    source.push_str("movz w10, #0xcdef\nmovk w10, #0xab, lsl #16\nstr w10, [x20, #44]\nldr w16, [x20, #44]\nldr x9, [x19, #136]\nadd x16, x9, x16\nbr x16\n");
    actual.extend([0x5280000a | (0xcdef << 5), 0x72a0000a | (0xab << 5),
        0xb9002e8a, 0xb9402e90, 0xf9404669, 0x8b100130, 0xd61f0200]);
    let input = dir.join("oracle.s"); let output = dir.join("oracle.o");
    std::fs::write(&input, source).unwrap();
    let clang = std::process::Command::new("xcrun").args(["--find", "clang"]).output().unwrap();
    assert!(clang.status.success());
    let clang = String::from_utf8(clang.stdout).unwrap();
    let assembled = std::process::Command::new(clang.trim()).args(["-target", "arm64-apple-macos14", "-c"])
        .arg(&input).arg("-o").arg(&output).output().unwrap();
    assert!(assembled.status.success(), "{}", String::from_utf8_lossy(&assembled.stderr));
    let data = std::fs::read(&output).unwrap(); assert!(data.len() < 512 * 1024);
    let u32_at = |at| u32::from_le_bytes(data[at..at + 4].try_into().unwrap()) as usize;
    assert_eq!(u32_at(0), 0xfeedfacf); let mut at = 32; let mut found = 0;
    for _ in 0..u32_at(16) {
        let size = u32_at(at + 4); assert!(size >= 8 && at + size <= data.len());
        if u32_at(at) == 0x19 {
            let n = u32_at(at + 64); assert_eq!(72 + n * 80, size);
            for i in 0..n {
                let section = at + 72 + i * 80;
                if &data[section..section + 16] == b"__text\0\0\0\0\0\0\0\0\0\0" {
                    let len = u64::from_le_bytes(data[section + 40..section + 48].try_into().unwrap()) as usize;
                    let start = u32_at(section + 48); assert_eq!(len % 4, 0); assert!(start + len <= data.len());
                    let expected: Vec<_> = data[start..start + len].chunks_exact(4)
                        .map(|bytes| u32::from_le_bytes(bytes.try_into().unwrap())).collect();
                    assert_eq!(actual, expected); found += 1;
                }
            }
        }
        at += size;
    }
    assert_eq!(found, 1);
    println!("independent assembler object: {} ({} words)", output.display(), actual.len());
}

#[test]
fn native_snapshots_preserve_exact_bytes_overlap_and_host_registers() {
    let mut code = platform::Code::reserve(512 * 1024).unwrap(); let mut entries = vec![];
    for size in 0..=400 {
        let mut a = Assembler::default();
        a.resumable_save_host(false);
        a.sub_imm(31, 31, 128);
        for q in 8..16 { a.emit(0x3d800000 | ((q - 8) << 10) | (31 << 5) | q); }
        for q in 8..16 {
            a.imm(9, 0xfeed000000000000 | q as u64);
            a.emit(0x9e670000 | (9 << 5) | q);
        }
        a.imm(16, 0x1357); a.imm(17, 0x2468); a.imm(22, 0x3579);
        a.mov(11, 2); a.mov(12, 1); a.abi_copy(size).unwrap();
        for q in 8..16 {
            a.emit(0x9e660000 | (q << 5) | 9); a.store64(9, 0, ((q - 8) * 8) as usize);
        }
        for (r, offset) in [(16, 64), (17, 72), (22, 80)] { a.store64(r, 0, offset); }
        for q in 8..16 { a.emit(0x3dc00000 | ((q - 8) << 10) | (31 << 5) | q); }
        a.add_imm(31, 31, 128); a.mov(0, 31); a.resumable_save_host(true); a.emit(0xd65f03c0);
        entries.push(code.append(&a.words).unwrap());
    }
    for (size, offset) in entries.into_iter().enumerate() {
        for alignment in 0..16 { for delta in [-400isize, -129, -17, -1, 0, 1, 17, 129, 400] {
            let source = 512 + alignment; let destination = (source as isize + delta) as usize;
            let mut memory: Vec<u8> = (0..1536).map(|n| ((n * 37 + n / 17) % 251) as u8).collect();
            let mut expected = memory.clone(); expected.copy_within(source..source + size, destination);
            let mut output = [0u128; 8];
            // SAFETY: the complete initialized source/destination ranges and
            // output remain stable through this synchronous owned leaf.
            let registers = unsafe { code.tree_abi_probe(offset, [output.as_mut_ptr() as usize,
                memory.as_mut_ptr().add(destination) as usize, memory.as_mut_ptr().add(source) as usize,
                0, 0, 0, 0, 0]) };
            assert_eq!(memory, expected, "size {size}, alignment {alignment}, delta {delta}");
            let lanes: Vec<u64> = output.into_iter().flat_map(|v| [v as u64, (v >> 64) as u64]).collect();
            for q in 8..16 { assert_eq!(lanes[q - 8], 0xfeed000000000000 | q as u64); }
            assert_eq!(&lanes[8..11], &[0x1357, 0x2468, 0x3579]);
            assert_eq!(&registers[..5], &[0, 0x1357, 0x2468, 0x3579, 0x468a]);
            assert_eq!(registers[5], registers[6]);
            assert_eq!(&registers[7..], &[0x579b, 0x68ac, 0x79bd, 0x8ace, 0x9bdf, 0xace0]);
        }}
    }
}
