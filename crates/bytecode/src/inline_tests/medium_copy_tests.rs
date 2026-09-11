use super::*;

fn aggregate_program(size: usize, second_source: usize, destination: usize,
                     formal_overlap: Option<usize>, cold: bool) -> Program {
    let span = (size + 15) & !15;
    let a_slot = span;
    let b_slot = formal_overlap.map_or(span * 2, |delta| span + delta);
    let frame_size = (b_slot + size).max(a_slot + size).max(size);
    let mut a: Vec<u8> = (0..size).map(|i| (i as u8).wrapping_mul(17).wrapping_add(3)).collect();
    a[0] = if cold { 255 } else { 0 };
    let b: Vec<u8> = (0..size).map(|i| (i as u8).wrapping_mul(29).wrapping_add(7)).collect();
    // Independent byte model includes overlapping caller operands and ordered
    // copies into overlapping callee argument slots.
    let mut caller = vec![0u8; 768];
    caller[32..32 + size].copy_from_slice(&a);
    caller[second_source..second_source + size].copy_from_slice(&b);
    let mut callee = vec![0u8; frame_size];
    callee[a_slot..a_slot + size].copy_from_slice(&caller[32..32 + size]);
    callee[b_slot..b_slot + size].copy_from_slice(&caller[second_source..second_source + size]);
    callee.copy_within(a_slot..a_slot + size, 0);
    let expected = callee[..size].to_vec();
    let mut data = vec![0; 16];
    data.extend_from_slice(&a);
    let b_data = data.len();
    data.extend_from_slice(&b);
    let expected_data = data.len();
    data.extend_from_slice(&expected);
    let mut code = vec![
        Op::Imm { dst: 0, value: 16 },
        Op::Local { dst: 1, offset: 32 },
        Op::Copy { dst: 1, src: 0, size },
        Op::Imm { dst: 0, value: b_data as u128 },
        Op::Local { dst: 2, offset: second_source },
        Op::Copy { dst: 2, src: 0, size },
        Op::Local { dst: 3, offset: destination },
        Op::Call { function: 1, args: vec![1, 2], destination: 3 },
        Op::Local { dst: 3, offset: destination },
        Op::Imm { dst: 4, value: expected_data as u128 },
        Op::Imm { dst: 5, value: size as u128 },
        Op::CompareBytes { dst: 6, left: 3, right: 4, size: 5 },
        Op::Local { dst: 7, offset: 0 },
        Op::Store { address: 7, src: 6, size: 8 },
    ];
    // Allow the existing bounded growth policy to select this synthetic call.
    code.extend((0..24).map(|value| Op::Imm { dst: 8, value }));
    code.push(Op::Return);
    Program {
        version: VERSION, target: "aarch64-apple-darwin".into(), entry: 0,
        data, statics: vec![], thread_locals: vec![],
        functions: vec![
            Function { name: "aggregate caller".into(), frame_size: 768,
                frame_align: 16, registers: 9, args: vec![],
                result: Slot { offset: 0, size: 8 }, code },
            leaf("aggregate leaf", frame_size, 2,
                vec![Slot { offset: a_slot, size }, Slot { offset: b_slot, size }],
                Slot { offset: 0, size },
                vec![Op::Local { dst: 0, offset: 0 },
                     Op::Local { dst: 1, offset: a_slot },
                     Op::Copy { dst: 0, src: 1, size }, Op::Return]),
        ],
    }
}

#[test]
fn medium_argument_and_result_copies_preserve_all_aliases() {
    for size in [33, 48, 80, 88, 112, 120, 128] {
        for second_source in [32, 40, 224] {
            for destination in [24, 32, 33, 216, 224, 225, 512] {
                for overlap in [None, Some(1), Some(size / 2)] {
                    let p = aggregate_program(size, second_source, destination, overlap, false);
                    let (q, stats) = inline::transform(&p, options()).unwrap();
                    assert_eq!(stats["selected_sites"], 1);
                    for engine in [Engine::Interpreter, Engine::Jit] {
                        assert_eq!(execute_with_engine(&p, &[], Limits::default(), engine).unwrap().value, 0);
                        assert_eq!(execute_with_engine(&q, &[], Limits::default(), engine).unwrap().value, 0);
                    }
                }
            }
        }
    }
}

#[test]
fn medium_leaf_preserves_cold_failure_and_exact_budgets() {
    for cold in [false, true] {
        let mut p = aggregate_program(80, 224, 32, None, cold);
        let f = &mut p.functions[1];
        f.registers = 3;
        f.code = vec![
            Op::Local { dst: 0, offset: 0 },
            Op::Local { dst: 1, offset: f.args[0].offset },
            Op::Load { dst: 2, address: 1, size: 1 },
            Op::Switch { value: 2, cases: vec![(255, 6)], otherwise: 4 },
            Op::Copy { dst: 0, src: 1, size: 80 },
            Op::Return,
            Op::Trap { message: "medium aggregate cold branch".into() },
        ];
        // Cross-block register reads still fail the unchanged conservative
        // eligibility proof. MIR lowering restates these addresses per block.
        assert!(crate::registers::needs_initial_zeroes_for_inlining(&p.functions[1]));
        assert_eq!(inline::transform(&p, options()).unwrap().1["selected_sites"], 0);
        let offset = p.functions[1].args[0].offset;
        p.functions[1].code.splice(4..4, [
            Op::Local { dst: 0, offset: 0 },
            Op::Local { dst: 1, offset },
        ]);
        let Op::Switch { cases, .. } = &mut p.functions[1].code[3] else { unreachable!() };
        cases[0].1 = 8;
        assert!(!crate::registers::needs_initial_zeroes_for_inlining(&p.functions[1]));
        let (q, stats) = inline::transform(&p, options()).unwrap();
        assert_eq!(stats["selected_sites"], 1);
        if cold {
            for program in [&p, &q] {
                for engine in [Engine::Interpreter, Engine::Jit] {
                    assert!(execute_with_engine(program, &[], Limits::default(), engine)
                        .unwrap_err().contains("medium aggregate cold branch"));
                }
            }
        } else {
            let expected = execute_with_engine(&q, &[], Limits::default(), Engine::Interpreter).unwrap();
            assert_eq!(expected.value, 0);
            for engine in [Engine::Interpreter, Engine::Jit] {
                let (profiled, _) = execute_profiled(&q, &[], Limits::default(), engine).unwrap();
                assert_eq!(profiled.value, 0);
                assert_eq!(profiled.instructions, expected.instructions);
                for instructions in 0..expected.instructions {
                    let limits = Limits { instructions, ..Limits::default() };
                    assert!(execute_with_engine(&q, &[], limits, engine)
                        .unwrap_err().contains("instruction limit"));
                }
                let exact = Limits { instructions: expected.instructions, ..Limits::default() };
                assert_eq!(execute_with_engine(&q, &[], exact, engine).unwrap().value, 0);
            }
        }
    }
}

#[test]
fn medium_leaf_keeps_copy_abi_and_frame_limits() {
    let p = aggregate_program(128, 224, 512, None, false);
    assert_eq!(inline::transform(&p, options()).unwrap().1["selected_sites"], 1);
    for limit in ["copy", "argument", "result", "frame"] {
        let mut rejected = p.clone();
        let f = &mut rejected.functions[1];
        match limit {
            "copy" => {
                let Op::Copy { size, .. } = &mut f.code[2] else { panic!("copy fixture"); };
                *size = 129;
            }
            "argument" => f.args[0].size = 129,
            "result" => f.result.size = 129,
            "frame" => f.frame_size = 513,
            _ => unreachable!(),
        }
        let (unchanged, stats) = inline::transform(&rejected, options()).unwrap();
        assert_eq!(stats["selected_sites"], 0, "{limit}");
        assert_eq!(bincode::serialize(&unchanged).unwrap(), bincode::serialize(&rejected).unwrap());
    }
    assert_eq!(inline::transform(&p, inline::Options { caller_growth: 1, ..options() }).unwrap().1["selected_sites"], 0);
}


#[test]
fn medium_leaf_frame_growth_includes_alignment_and_exact_boundary() {
    for (caller_frame, selected) in [(479, 0), (480, 1), (481, 0), (512, 1)] {
        let mut p = aggregate_program(80, 224, 32, None, false);
        p.functions[0].frame_size = caller_frame;
        assert_eq!(p.functions[1].frame_size, 240);
        let (q, stats) = inline::transform(&p, options()).unwrap();
        assert_eq!(stats["selected_sites"], selected, "frame {caller_frame}");
        if selected == 0 {
            assert_eq!(bincode::serialize(&p).unwrap(), bincode::serialize(&q).unwrap());
        } else {
            assert!(q.functions[0].frame_size - caller_frame <= caller_frame / 2);
        }
        for program in [&p, &q] {
            for engine in [Engine::Interpreter, Engine::Jit] {
                assert_eq!(execute_with_engine(program, &[], Limits::default(), engine).unwrap().value, 0);
            }
        }
    }
}

#[test]
fn medium_frame_guard_covers_body_and_abi_but_preserves_small_leaves() {
    for kind in ["small", "body", "argument", "result"] {
        let mut p = aggregate_program(32, 128, 32, None, false);
        p.functions[0].frame_size = 192;
        p.functions[1].frame_size = 512;
        let leaf = &mut p.functions[1];
        match kind {
            "small" => {},
            "body" => {
                let Op::Copy { size, .. } = &mut leaf.code[2] else { unreachable!() };
                *size = 33;
            },
            "argument" => leaf.args[1].size = 33,
            "result" => leaf.result.size = 33,
            _ => unreachable!(),
        }
        let (q, stats) = inline::transform(&p, options()).unwrap();
        assert_eq!(stats["selected_sites"], if kind == "small" { 1 } else { 0 }, "{kind}");
        if kind != "small" {
            assert_eq!(bincode::serialize(&p).unwrap(), bincode::serialize(&q).unwrap());
        }
        // The caller checks the original 32 result bytes. Extended body/ABI
        // copies may affect adjacent bytes, so compare the whole executions
        // as well as the independent model's observable result.
        for program in [&p, &q] {
            for engine in [Engine::Interpreter, Engine::Jit] {
                assert_eq!(execute_with_engine(program, &[], Limits::default(), engine).unwrap().value, 0);
            }
        }
    }
}
