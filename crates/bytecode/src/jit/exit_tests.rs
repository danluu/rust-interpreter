use super::*;
use crate::{Slot, VERSION};

#[test]
fn successful_native_exits_require_interpretation_at_the_remaining_budget() {
    let imm = |dst, value| Op::Imm { dst, value };
    let mut cases = vec![
        vec![imm(0, 7), imm(1, 9), imm(2, 11), Op::Return],
        // Returning code_len lets the VM preserve budget-before-invalid-PC order.
        vec![imm(0, 7), imm(1, 9), imm(2, 11)],
        vec![
            imm(0, 7),
            imm(1, 9),
            imm(2, 11),
            Op::Unary {
                dst: 3,
                src: 0,
                bits: 128,
                op: Unary::CountOnes,
            },
            imm(0, 1),
            imm(1, 2),
            imm(2, 3),
            Op::Return,
        ],
        vec![
            imm(0, 3),
            imm(1, 1),
            imm(2, 0),
            Op::Binary {
                dst: 0,
                overflow: 4,
                a: 0,
                b: 1,
                bits: 64,
                signed: false,
                op: Binary::Sub,
            },
            imm(3, 19),
            Op::Switch {
                value: 0,
                cases: vec![(0, 6)],
                otherwise: 3,
            },
            Op::Return,
        ],
        vec![
            imm(0, 7),
            imm(1, 9),
            imm(2, 11),
            Op::Switch {
                value: 0,
                cases: (0..17).map(|n| (n, 4)).collect(),
                otherwise: 4,
            },
            Op::Return,
        ],
    ];
    for value in [0, 1] {
        cases.push(vec![
            imm(0, value),
            imm(1, 9),
            imm(2, 11),
            Op::Switch {
                value: 0,
                cases: vec![(0, 4)],
                otherwise: 5,
            },
            Op::Return,
            imm(1, 17),
            imm(2, 19),
            Op::Return,
        ]);
    }
    // Include the forced 1024-operation region split and its native successor.
    let mut long: Vec<_> = (0..1030).map(|n| imm(0, n)).collect();
    long.push(Op::Return);
    cases.push(long);
    for (index, code) in cases.into_iter().enumerate() {
        let p = Program {
            version: VERSION,
            target: "aarch64-apple-darwin".into(),
            entry: 0,
            data: vec![0; 64],
            statics: vec![],
            thread_locals: vec![],
            functions: vec![Function {
                name: format!("exit_{index}"),
                frame_size: 16,
                frame_align: 16,
                registers: 8,
                args: vec![],
                result: Slot { offset: 0, size: 0 },
                code,
            }],
        };
        crate::validate(&p).unwrap();
        for profiled in [false, true] {
            let mut jit = Jit::new(&p, profiled, MAX_CODE_BYTES).unwrap();
            jit.ensure_function(0).unwrap();
            let length = p.functions[0].code.len();
            for (entry, block) in jit.blocks[0]
                .iter()
                .enumerate()
                .filter_map(|(pc, block)| block.map(|block| (pc, block)))
            {
                for budget in 0..=(length as u64 + 16) {
                    let mut registers = [0u128; 8];
                    let mut memory = [0u8; 96];
                    let mut hits = vec![0u64; length];
                    let result = unsafe {
                        jit.run(
                            block,
                            length,
                            budget,
                            if profiled {
                                hits.as_mut_ptr()
                            } else {
                                std::ptr::null_mut()
                            },
                            registers.as_mut_ptr(),
                            64,
                            memory.as_mut_ptr(),
                            memory.len(),
                            64,
                            std::ptr::null_mut(),
                            0,
                        )
                    };
                    // execute_observed checks this minimum before calling run().
                    if budget < (block.end - entry) as u64 {
                        assert_eq!(result.unwrap_err(), "JIT made no instruction progress");
                        assert!(hits.iter().all(|count| *count == 0));
                        continue;
                    }
                    let (next, executed) = result.unwrap();
                    assert!(next <= length);
                    assert!(executed <= budget);
                    assert!(
                        jit.blocks[0].get(next).copied().flatten().is_none_or(
                            |successor| (successor.end - next) as u64 > budget - executed
                        ),
                        "case={index} budget={budget} next={next} executed={executed}"
                    );
                    if profiled {
                        let charged: u64 = hits
                            .iter()
                            .enumerate()
                            .filter(|(_, count)| **count != 0)
                            .map(|(pc, count)| count * (jit.blocks[0][pc].unwrap().end - pc) as u64)
                            .sum();
                        assert_eq!(charged, executed);
                    }
                }
            }
        }
    }
}
