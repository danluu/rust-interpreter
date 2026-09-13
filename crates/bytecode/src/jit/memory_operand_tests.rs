use super::*;
use crate::{Engine, Limits, Slot, VERSION, execute_with_engine};

#[test]
fn memory_loads_define_both_words_without_overwritten_clears() {
    for size in 0..=16 {
        let mut a = Assembler::default();
        a.load_mem(9, 10, 11, size);
        let zero_lo = 0xaa1f03e9;
        let zero_hi = 0xaa1f03ea;
        if [1, 2, 4, 8, 16].contains(&size) {
            assert_eq!(a.words.len(), 2);
            assert!(!a.words.contains(&zero_lo));
            assert_eq!(a.words.contains(&zero_hi), size != 16);
            let load = match size { 1 => 0x39400169, 2 => 0x79400169,
                4 => 0xb9400169, _ => 0xf9400169 };
            assert!(a.words.contains(&load));
            if size == 16 { assert_eq!(a.words[1], 0xf940056a); }
        } else {
            assert_eq!(&a.words[..2], &[zero_lo, zero_hi]);
            assert_eq!(a.words.len(), 2 + size * 2);
        }
        if size <= 8 {
            let mut discarded = Assembler::default();
            discarded.load_mem_at(9, 31, 11, size, 0);
            assert_eq!(discarded.words.len() + 1, a.words.len());
            assert!(!discarded.words.contains(&0xaa1f03ff)); // No mov xzr,xzr.
        }
    }
    let mut a = Assembler::default();
    a.load_mem_at(9, 10, 11, 16, 4094);
    a.store_mem_at(9, 10, 11, 16, 4094);
    assert_eq!(a.words, [0xf97ff969, 0xf97ffd6a, 0xf93ff969, 0xf93ffd6a]);
}

#[test]
fn displaced_memory_uses_only_complete_aligned_encodable_local_ranges() {
    let cases = [(0, 0, false), (0, 1, true), (4095, 1, true), (4096, 1, false),
        (8190, 2, true), (8192, 2, false), (16380, 4, true), (16384, 4, false),
        (32760, 8, true), (32768, 8, false), (32752, 16, true), (32760, 16, false),
        (1, 8, false), (3, 3, false), (65536, 1, false), (usize::MAX, 16, false)];
    for (offset, size, folded) in cases {
        for write in [false, true] {
            let make = || {
                let mut a = Assembler { frame_size: 65536, heap: true, ..Assembler::default() };
                a.facts.insert(0, Fact::Local(offset));
                a
            };
            let mut a = make();
            let immediate = a.memory_address(11, 0, size, write);
            if folded {
                assert_eq!(immediate as usize, offset / size.min(8));
                assert_eq!(a.words, [0x8b01004b]); // add x11,x2,x1
                assert!(a.failures.is_empty());
            } else {
                let mut reference = make();
                reference.address(11, 0, size, write);
                assert_eq!(immediate, 0);
                assert_eq!(a.words, reference.words);
                assert_eq!(a.failures.len(), reference.failures.len());
            }
        }
    }
    // A nonlocal/unknown address retains exactly the original checked path.
    for write in [false, true] {
        let mut a = Assembler { heap: true, ..Assembler::default() };
        let mut reference = Assembler { heap: true, ..Assembler::default() };
        assert_eq!(a.memory_address(11, 0, 16, write), 0);
        reference.address(11, 0, 16, write);
        assert_eq!(a.words, reference.words);
        assert!(!a.failures.is_empty());
    }
}

#[test]
fn narrow_stores_do_not_read_an_unused_high_operand() {
    for src in [1, 2048] {
        for size in 0..=16 {
            let reads = vec![Some((0, 1)); src as usize + 1];
            let mut a = Assembler { frame_size: 64, reads: &reads, ..Assembler::default() };
            a.facts.insert(0, Fact::Local(16));
            a.lower(&Op::Store { address: 0, src, size });
            let high_reads = a.words.iter().filter(|&&w| w & 0xffc0001f == 0xf940000a).count();
            assert_eq!(high_reads, usize::from(size > 8), "size={size}, src={src}");
            assert!(a.live_in.contains(&src));
        }
    }
}

#[test]
fn scalar_local_copies_share_one_base_and_load_before_storing() {
    for size in [1, 2, 4, 8, 16] {
        let scale = size.min(8);
        for (source, destination) in [(0, 0), (16, 24), (4088 * scale, 4094 * scale)] {
            let mut a = Assembler { frame_size: 65536, ..Assembler::default() };
            a.facts.insert(0, Fact::Local(source));
            a.facts.insert(1, Fact::Local(destination));
            a.lower(&Op::Copy { dst: 1, src: 0, size });
            let load = match size { 1 => 0x39400169, 2 => 0x79400169,
                4 => 0xb9400169, _ => 0xf9400169 };
            let store = match size { 1 => 0x39000169, 2 => 0x79000169,
                4 => 0xb9000169, _ => 0xf9000169 };
            let src = (source / scale) as u32;
            let dst = (destination / scale) as u32;
            let expected = if size == 16 {
                vec![0x8b01004b, load | (src << 10), 0xf940016a | ((src + 1) << 10),
                    store | (dst << 10), 0xf900016a | ((dst + 1) << 10)]
            } else { vec![0x8b01004b, load | (src << 10), store | (dst << 10)] };
            assert_eq!(a.words, expected, "size={size}, src={source}, dst={destination}");
            assert!(a.failures.is_empty());
        }
    }
}

#[test]
fn scalar_copy_fallbacks_keep_checks_and_non_scalar_emission() {
    for size in 0..=16 {
        for local in [false, true] {
            let make = || {
                let mut a = Assembler { frame_size: 65536, heap: true, ..Assembler::default() };
                if local {
                    // Just beyond every scalar immediate, with unaligned
                    // addresses for wider accesses. Both ranges remain valid.
                    a.facts.insert(0, Fact::Local(40001));
                    a.facts.insert(1, Fact::Local(40003));
                }
                a
            };
            let mut actual = make();
            actual.lower(&Op::Copy { dst: 1, src: 0, size });
            let mut original = make();
            original.address(11, 0, size, false);
            original.address(12, 1, size, true);
            // The only remaining change for unencodable/unknown addresses is
            // omission of the unused narrow high-word clear.
            let high = if [1, 2, 4, 8].contains(&size) { 31 } else { 10 };
            original.load_mem(9, high, 11, size);
            original.store_mem(9, high, 12, size);
            assert_eq!(actual.words, original.words, "size={size}, local={local}");
            assert_eq!(actual.failures.len(), original.failures.len());
            assert_eq!(actual.live_in, original.live_in);
        }
    }
}

#[test]
fn memory_operands_preserve_bytes_across_widths_alignments_exits_and_budget_tails() {
    const VALUE: u128 = 0xfedc_ba98_7654_3210_0123_4567_89ab_cdef;
    for size in 0..=16 {
        let mask = if size == 16 { u128::MAX } else { (1u128 << (size * 8)) - 1 };
        for offset in [0, 1, 8, 255, 256, 4095, 4096, 32752, 32760, 32768] {
            for frame_align in [1, 2, 16] {
                for read_size in [size, 16] {
                    let result_offset = offset.max(16) + 16;
                    let barrier = Op::Binary { dst: 3, overflow: 4, op: Binary::Mul,
                        a: 1, b: 1, bits: 128, signed: false };
                    assert!(!supported(&barrier));
                    let program = Program {
                        version: VERSION, target: "aarch64-apple-darwin".into(), entry: 0,
                        data: vec![0; 65], statics: vec![], thread_locals: vec![],
                        functions: vec![Function { name: "memory-operands".into(),
                            frame_size: result_offset + 16, frame_align, registers: 8,
                            args: vec![Slot { offset: 0, size: 16 }],
                            result: Slot { offset: result_offset, size: 16 },
                            code: vec![Op::Local { dst: 0, offset: 0 },
                                Op::Load { dst: 1, address: 0, size: 16 },
                                Op::Local { dst: 2, offset },
                                Op::Imm { dst: 7, value: !VALUE },
                                Op::Store { address: 2, src: 7, size: 16 },
                                Op::Store { address: 2, src: 1, size },
                                barrier,
                                // Reestablish the Local fact after a real VM
                                // exit. The load cannot forward from the store.
                                Op::Local { dst: 2, offset },
                                Op::Load { dst: 5, address: 2, size: read_size },
                                Op::Local { dst: 6, offset: result_offset },
                                Op::Store { address: 6, src: 5, size: 16 }, Op::Return] }],
                    };
                    crate::validate(&program).unwrap();
                    let reference = execute_with_engine(&program, &[VALUE], Limits::default(), Engine::Interpreter).unwrap();
                    let expected_value = (VALUE & mask) | if read_size == 16 { !VALUE & !mask } else { 0 };
                    assert_eq!(reference.value, expected_value);
                    for (persistent, resumable) in [(false, false), (true, false), (false, true), (true, true)] {
                        for budget in 0..=reference.instructions + 1 {
                            let expected = execute_with_engine(&program, &[VALUE],
                                Limits { instructions: budget, ..Limits::default() }, Engine::Interpreter);
                            let actual = execute_with_engine(&program, &[VALUE], Limits {
                                instructions: budget, jit_resumable_calls: resumable,
                                jit_persistent_registers: persistent, ..Limits::default()
                            }, Engine::Jit);
                            match (expected, actual) {
                                (Ok(a), Ok(b)) => {
                                    assert_eq!((a.value, a.instructions, a.peak_memory), (b.value, b.instructions, b.peak_memory));
                                    assert!(b.jit_instructions > 0);
                                }
                                (Err(a), Err(b)) => assert_eq!(a, b),
                                pair => panic!("size={size}, offset={offset}, align={frame_align}, read={read_size}, budget={budget}: {pair:?}"),
                            }
                        }
                    }
                }
            }
        }
    }
}

#[test]
fn scalar_copies_preserve_live_wide_values_native_calls_and_every_budget() {
    use crate::execute_profiled;
    const VALUE: u128 = 0xfedc_ba98_7654_3210_0123_4567_89ab_cdef;
    for size in [1, 2, 4, 8, 16] {
        for offset in [128, 129, 32752, 32760, 32768] {
            let mask = if size == 16 { u128::MAX } else { (1u128 << (size * 8)) - 1 };
            let expected_value = ((VALUE & mask) | (!VALUE & !mask)).wrapping_sub(VALUE);
            let p = Program { version: VERSION, target: "aarch64-apple-darwin".into(), entry: 0,
                data: vec![0; 65], statics: vec![], thread_locals: vec![],
                functions: vec![Function { name: "copy caller".into(), frame_size: 48, frame_align: 2,
                    registers: 2, args: vec![Slot { offset: 16, size: 16 }], result: Slot { offset: 0, size: 16 },
                    code: vec![Op::Local { dst: 0, offset: 16 }, Op::Load { dst: 1, address: 0, size: 16 },
                        Op::Local { dst: 0, offset: 0 }, Op::Call { function: 1, args: vec![1], destination: 0 },
                        Op::Return] },
                    Function { name: "copy callee".into(), frame_size: offset + 16, frame_align: 1,
                        registers: 9, args: vec![Slot { offset: 16, size: 16 }], result: Slot { offset: 0, size: 16 },
                        code: vec![Op::Local { dst: 0, offset: 16 }, Op::Load { dst: 1, address: 0, size: 16 },
                            Op::Local { dst: 2, offset }, Op::Imm { dst: 3, value: !VALUE },
                            Op::Store { address: 2, src: 3, size: 16 }, Op::Copy { dst: 2, src: 0, size },
                            Op::Load { dst: 5, address: 2, size: 16 },
                            Op::Binary { dst: 6, overflow: 7, op: Binary::Sub, a: 5, b: 1, bits: 128, signed: false },
                            Op::Local { dst: 8, offset: 0 }, Op::Store { address: 8, src: 6, size: 16 }, Op::Return] }] };
            crate::validate(&p).unwrap();
            let complete = execute_with_engine(&p, &[VALUE], Limits::default(), Engine::Interpreter).unwrap();
            assert_eq!(complete.value, expected_value);
            for budget in 0..=complete.instructions + 1 {
                let reference = execute_profiled(&p, &[VALUE], Limits { instructions: budget, ..Limits::default() }, Engine::Interpreter);
                for capacity in [0, MAX_CODE_BYTES] { for persistent in [false, true] { for resumable in [false, true] {
                    let limits = || Limits { instructions: budget, jit_code_bytes: capacity,
                        jit_persistent_registers: persistent, jit_resumable_calls: resumable, ..Limits::default() };
                    let normal = execute_with_engine(&p, &[VALUE], limits(), Engine::Jit);
                    let observed = execute_profiled(&p, &[VALUE], limits(), Engine::Jit);
                    match &reference {
                        Err(error) => { assert_eq!(&normal.unwrap_err(), error); assert_eq!(&observed.unwrap_err(), error); }
                        Ok((result, reference_profile)) => {
                            let normal = normal.unwrap(); let (observed, profile) = observed.unwrap();
                            for actual in [normal, observed] {
                                assert_eq!((actual.value, actual.instructions, actual.peak_memory),
                                    (result.value, result.instructions, result.peak_memory));
                                if capacity != 0 { assert!(actual.jit_instructions > 0); }
                            }
                            for (f, r) in profile.functions.iter().zip(&reference_profile.functions) {
                                let mut counts = f.interpreted.clone();
                                for (start, &hits) in f.jit_blocks.iter().enumerate() {
                                    if hits != 0 { for count in &mut counts[start..f.jit_block_ends[start]] { *count += hits; } }
                                }
                                assert_eq!(counts, r.interpreted);
                            }
                        }
                    }
                }}}
            }
        }
    }
}
