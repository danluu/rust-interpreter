use super::*;
use crate::{Slot, VERSION};

fn function(code: Vec<Op>) -> Function {
    Function {
        name: "mixed ABI".into(),
        frame_size: 16,
        frame_align: 16,
        registers: 4,
        args: vec![],
        result: Slot { offset: 0, size: 8 },
        code,
    }
}

#[test]
fn mixed_native_frames_restore_the_abi_for_declines_returns_and_every_fault_position() {
    for depth in [1, 2, trees::MAX_DEPTH] {
        // Child traps, child assertions, argument faults, result faults and
        // ordinary-region faults all unwind through different emitted tails.
        for fault in ["none", "trap", "assert", "argument", "result", "after"] {
            let mut functions = vec![function(vec![
                if fault == "result" {
                    Op::Imm { dst: 0, value: 0 }
                } else {
                    Op::Local { dst: 0, offset: 0 }
                },
                Op::Imm { dst: 1, value: 0 },
                Op::Imm { dst: 2, value: 2 },
                Op::Call {
                    function: 1,
                    args: if fault == "argument" { vec![1] } else { vec![] },
                    destination: 0,
                },
                if fault == "after" {
                    Op::Load {
                        dst: 2,
                        address: 1,
                        size: 8,
                    }
                } else {
                    Op::Imm { dst: 2, value: 3 }
                },
                Op::Imm { dst: 1, value: 1 },
                Op::Jump { target: 7 },
                Op::Return,
            ])];
            for id in 1..=depth {
                functions.push(function(if id == depth {
                    match fault {
                        "trap" => vec![Op::Trap {
                            message: "nested trap".into(),
                        }],
                        "assert" => vec![
                            Op::Assert {
                                value: 3,
                                expected: true,
                                message: "nested assertion".into(),
                            },
                            Op::Return,
                        ],
                        _ => vec![Op::Return],
                    }
                } else {
                    vec![
                        Op::Local { dst: 0, offset: 0 },
                        Op::Call {
                            function: id + 1,
                            args: vec![],
                            destination: 0,
                        },
                        Op::Return,
                    ]
                }));
            }
            if fault == "argument" {
                functions[1].args = vec![Slot { offset: 0, size: 8 }];
            }
            let p = Program {
                version: VERSION,
                target: "aarch64-apple-darwin".into(),
                entry: 0,
                functions,
                data: vec![0; 16],
                statics: vec![],
                thread_locals: vec![],
            };
            crate::validate(&p).unwrap();
            for profiled in [false, true] {
                let mut jit = Jit::new_with_call_stubs(&p, profiled, MAX_CODE_BYTES, true).unwrap();
                jit.ensure_function(0).unwrap();
                let plan = jit.ready_tree(1).unwrap().0;
                let (end, register_end, _) = jit.region_plans[0].requirements(32, 4).unwrap();
                for ready in [false, true] {
                    for budget in [
                        0,
                        2,
                        3,
                        4,
                        plan.instructions + 3,
                        plan.instructions + 4,
                        plan.instructions + 7,
                    ] {
                        for pc in [0, 3, 4] {
                            let mut memory = vec![0; end + 32];
                            memory[end..].fill(0xad);
                            let mut registers = vec![0u128; register_end];
                            registers[0] = if fault == "result" { 0 } else { 16 };
                            let mut hits: Vec<Vec<u64>> =
                                p.functions.iter().map(|f| vec![0; f.code.len()]).collect();
                            let table: Vec<_> = hits.iter_mut().map(|h| h.as_mut_ptr()).collect();
                            let mut ordinary = vec![0; p.functions[0].code.len()];
                            let mut cursor = TreeCursor {
                                base: Cursor {
                                    remaining: budget,
                                    profile_hits: ordinary.as_mut_ptr(),
                                },
                                memory_len: 32,
                                peak_linear: 32,
                                return_address: 0,
                                profile_table: table.as_ptr(),
                                calls: 0,
                                tree_instructions: 0,
                                regions_ready: u64::from(ready),
                                stub_calls: 0,
                            };
                            let arguments = [
                                registers.as_mut_ptr() as usize,
                                16,
                                memory.as_mut_ptr() as usize,
                                32,
                                16,
                                0,
                                0,
                                std::ptr::addr_of_mut!(cursor) as usize,
                            ];
                            let block = jit.blocks[0][pc].unwrap();
                            let output = unsafe {
                                jit.code
                                    .as_ref()
                                    .unwrap()
                                    .tree_abi_probe(block.offset, arguments)
                            };
                            assert_eq!(&output[1..5], &[0x1357, 0x2468, 0x3579, 0x468a]);
                            assert_eq!(
                                &output[7..],
                                &[0x579b, 0x68ac, 0x79bd, 0x8ace, 0x9bdf, 0xace0]
                            );
                            assert_eq!(output[5], output[6]);
                            assert_eq!(output[6] % 16, 0);
                            assert!(cursor.base.remaining <= budget);
                            assert!(memory[end..].iter().all(|&b| b == 0xad));
                            let prior = if pc == 0 { 3 } else { 0 };
                            let reached_child =
                                pc != 4 && ready && budget >= prior + 1 + plan.instructions;
                            if !ready {
                                assert_eq!((cursor.calls, cursor.stub_calls), (0, 0));
                            }
                            let reaches_after = pc == 4 && budget >= 3
                                || reached_child && budget >= prior + 1 + plan.instructions + 3;
                            let expected_fault = reached_child
                                && ["trap", "assert", "argument", "result"].contains(&fault)
                                || reaches_after && fault == "after";
                            if expected_fault {
                                assert!(
                                    output[0] as u64 >= FAILURE_MIN,
                                    "depth={depth} fault={fault} ready={ready} budget={budget} pc={pc}"
                                );
                            } else {
                                assert!([0, 3, 4, 7].contains(&output[0]));
                                if reached_child {
                                    assert_eq!(cursor.stub_calls, 1);
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

#[test]
fn region_storage_bounds_include_padding_and_checked_overflow() {
    let mut plan = RegionPlan::default();
    plan.add(trees::Plan {
        instructions: 1,
        depth: 2,
        frame_span: 33,
        register_slots: 7,
        frame_align: 64,
    });
    plan.add(trees::Plan {
        instructions: 1,
        depth: 1,
        frame_span: 17,
        register_slots: 9,
        frame_align: 128,
    });
    assert_eq!(plan.requirements(129, 4), Some((289, 13, 256)));
    assert_eq!(plan.depth, 2);
    assert_eq!(plan.requirements(usize::MAX, 0), None);
    assert_eq!(plan.requirements(0, usize::MAX), None);
}
