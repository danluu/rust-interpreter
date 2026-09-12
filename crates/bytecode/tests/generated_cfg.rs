use rust_interp_bytecode::{Binary, Function, Op, Program, Reg, Slot, Unary, VERSION, validate};

struct Random(u64);
impl Random {
    fn next(&mut self) -> u64 {
        self.0 = self.0.wrapping_add(0x9e3779b97f4a7c15);
        let mut value = self.0;
        value = (value ^ (value >> 30)).wrapping_mul(0xbf58476d1ce4e5b9);
        value = (value ^ (value >> 27)).wrapping_mul(0x94d049bb133111eb);
        value ^ (value >> 31)
    }
    fn pick(&mut self, count: u64) -> usize {
        (self.next() % count) as usize
    }
    fn value(&mut self) -> Reg {
        8 + self.pick(16) as Reg
    }
    fn address(&mut self) -> Reg {
        self.pick(8) as Reg
    }
    fn bits(&mut self) -> u8 {
        [8, 16, 32, 64, 128][self.pick(5)]
    }
    fn op(&mut self) -> Op {
        match self.pick(7) {
            0 | 1 => Op::Binary {
                dst: self.value(),
                overflow: self.value(),
                op: [
                    Binary::Add,
                    Binary::Sub,
                    Binary::Mul,
                    Binary::And,
                    Binary::Or,
                    Binary::Xor,
                    Binary::Shl,
                    Binary::Shr,
                    Binary::Eq,
                    Binary::Lt,
                    Binary::Cmp,
                    Binary::RotateLeft,
                    Binary::RotateRight,
                ][self.pick(13)],
                a: self.value(),
                b: self.value(),
                bits: self.bits(),
                signed: self.pick(2) == 0,
            },
            2 => Op::Cast {
                dst: self.value(),
                src: self.value(),
                from: self.bits(),
                to: self.bits(),
                signed: self.pick(2) == 0,
            },
            3 => Op::Load {
                dst: self.value(),
                address: self.address(),
                size: self.pick(17) as u8,
            },
            4 => Op::Store {
                address: self.address(),
                src: self.value(),
                size: self.pick(17) as u8,
            },
            5 => Op::Copy {
                dst: self.address(),
                src: self.address(),
                size: self.pick(33),
            },
            _ if self.pick(2) == 0 => Op::Unary {
                dst: self.value(),
                src: self.value(),
                op: [
                    Unary::Not,
                    Unary::Neg,
                    Unary::CountOnes,
                    Unary::LeadingZeros,
                    Unary::TrailingZeros,
                    Unary::SwapBytes,
                ][self.pick(6)],
                bits: self.bits(),
            },
            _ => Op::Select {
                dst: self.value(),
                condition: self.value(),
                yes: self.value(),
                no: self.value(),
            },
        }
    }
}

fn function(random: &mut Random, root: bool) -> Function {
    let mut code = vec![];
    for reg in 0..6 {
        code.push(Op::Local {
            dst: reg,
            offset: reg as usize * 16,
        });
    }
    for reg in 8..24 {
        code.push(Op::Imm {
            dst: 28,
            value: 16 + (reg - 8) as u128 * 16,
        });
        code.push(Op::Load {
            dst: reg,
            address: 28,
            size: 16,
        });
    }
    code.extend([
        Op::Load {
            dst: 8,
            address: 0,
            size: 16,
        },
        Op::Imm {
            dst: 30,
            value: 128,
        },
        Op::Imm { dst: 31, value: 16 },
        Op::Allocate {
            dst: 6,
            size: 30,
            align: 31,
            zeroed: true,
        },
        Op::Imm {
            dst: 31,
            value: random.pick(32) as u128,
        },
        Op::Binary {
            dst: 7,
            overflow: 43,
            op: Binary::Add,
            a: 6,
            b: 31,
            bits: 64,
            signed: false,
        },
        Op::Imm {
            dst: 40,
            value: 2 + random.pick(if root { 5 } else { 2 }) as u128,
        },
        Op::Imm { dst: 41, value: 1 },
    ]);
    let loop_start = code.len();
    for _ in 0..5 {
        code.push(random.op());
    }
    code.push(Op::Binary {
        dst: 42,
        overflow: 43,
        op: Binary::And,
        a: 40,
        b: 41,
        bits: 64,
        signed: false,
    });
    let diamond = code.len();
    code.push(Op::Jump { target: 0 });
    let left = code.len();
    for _ in 0..4 {
        code.push(random.op());
    }
    if root {
        code.push(Op::Call {
            function: 1,
            args: vec![random.address()],
            destination: 1,
        });
        code.push(Op::Load {
            dst: random.value(),
            address: 1,
            size: 16,
        });
    }
    let join_jump = code.len();
    code.push(Op::Jump { target: 0 });
    let right = code.len();
    for _ in 0..4 {
        code.push(random.op());
    }
    if root {
        code.push(Op::Call {
            function: 1,
            args: vec![random.address()],
            destination: 1,
        });
        code.push(Op::Load {
            dst: random.value(),
            address: 1,
            size: 16,
        });
    }
    let join = code.len();
    code[diamond] = Op::Switch {
        value: 42,
        cases: vec![(0, left)],
        otherwise: right,
    };
    code[join_jump] = Op::Jump { target: join };
    for _ in 0..3 {
        code.push(random.op());
    }
    code.push(Op::Binary {
        dst: 40,
        overflow: 43,
        op: Binary::Sub,
        a: 40,
        b: 41,
        bits: 64,
        signed: false,
    });
    let backedge = code.len();
    code.push(Op::Switch {
        value: 40,
        cases: vec![(0, backedge + 1)],
        otherwise: loop_start,
    });
    code.push(Op::Imm { dst: 30, value: 0 });
    // Observe mutable values and every byte of the local/heap working areas.
    // Rotation makes positional changes observable instead of a plain XOR sum.
    for source in 8..24 {
        code.push(Op::Unary {
            dst: 30,
            src: 30,
            op: Unary::SwapBytes,
            bits: 128,
        });
        code.push(Op::Binary {
            dst: 30,
            overflow: 43,
            op: Binary::Sub,
            a: 30,
            b: source,
            bits: 128,
            signed: false,
        });
    }
    for heap in [false, true] {
        for offset in (0..128).step_by(16) {
            if heap {
                code.push(Op::Imm {
                    dst: 31,
                    value: offset as u128,
                });
                code.push(Op::Binary {
                    dst: 29,
                    overflow: 43,
                    op: Binary::Add,
                    a: 6,
                    b: 31,
                    bits: 64,
                    signed: false,
                });
            } else {
                code.push(Op::Local { dst: 29, offset });
            }
            code.push(Op::Load {
                dst: 31,
                address: 29,
                size: 16,
            });
            code.push(Op::Unary {
                dst: 30,
                src: 30,
                op: Unary::SwapBytes,
                bits: 128,
            });
            code.push(Op::Binary {
                dst: 30,
                overflow: 43,
                op: Binary::Sub,
                a: 30,
                b: 31,
                bits: 128,
                signed: false,
            });
        }
    }
    code.extend([
        Op::Store {
            address: 1,
            src: 30,
            size: 16,
        },
        Op::Imm {
            dst: 30,
            value: 128,
        },
        Op::Imm { dst: 31, value: 16 },
        Op::Deallocate {
            pointer: 6,
            size: 30,
            align: 31,
        },
        Op::Return,
    ]);
    Function {
        name: if root {
            "generated root"
        } else {
            "generated callee"
        }
        .into(),
        frame_size: 256,
        frame_align: 16,
        registers: 48,
        args: vec![Slot {
            offset: 0,
            size: 16,
        }],
        result: Slot {
            offset: 16,
            size: 16,
        },
        code,
    }
}

fn program(seed: u64) -> Program {
    let mut random = Random(seed);
    let data = (0..288).map(|_| random.next() as u8).collect();
    Program {
        version: VERSION,
        target: "aarch64-apple-darwin".into(),
        entry: 0,
        data,
        statics: vec![],
        thread_locals: vec![],
        functions: vec![function(&mut random, true), function(&mut random, false)],
    }
}

#[test]
fn generated_programs_are_bounded_valid_and_reproducible() {
    for seed in (0..64).chain([u64::MAX, 1 << 63]) {
        let p = program(seed);
        validate(&p).unwrap();
        assert_eq!(
            bincode::serialize(&p).unwrap(),
            bincode::serialize(&program(seed)).unwrap()
        );
        assert!(p.functions.iter().all(|f| f.code.len() < 256));
    }
}

#[cfg(all(target_arch = "aarch64", target_os = "macos"))]
mod native {
    use super::*;
    use rust_interp_bytecode::{
        Engine, Execution, ExecutionProfile, Limits, execute_profiled, execute_with_engine,
    };
    use std::io::Write;

    fn result(r: &Result<Execution, String>) -> Result<(u128, u64, usize), &str> {
        r.as_ref()
            .map(|e| (e.value, e.instructions, e.peak_memory))
            .map_err(String::as_str)
    }

    fn fail(seed: u64, p: &Program, argument: u128, settings: &str, details: String) -> ! {
        let root = std::env::var_os("RUST_INTERP_DIFF_OUTPUT")
            .map(std::path::PathBuf::from)
            .unwrap_or_else(|| {
                std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
                    .join("../../.work/generated-cfg-failures")
            });
        std::fs::create_dir_all(&root).unwrap();
        let stamp = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_nanos();
        let directory = root.join(format!("seed-{seed}-{}-{stamp}", std::process::id()));
        std::fs::create_dir(&directory).unwrap();
        for (name, bytes) in [
            ("program.rbc", bincode::serialize(p).unwrap()),
            ("reproduction.json", serde_json::to_vec_pretty(&serde_json::json!({
                "seed": seed, "argument": argument.to_string(), "settings": settings,
                "details": details, "scope": "generated valid bytecode; no frontend coverage claim"
            })).unwrap()),
        ] {
            let mut file = std::fs::OpenOptions::new().write(true).create_new(true).open(directory.join(name)).unwrap();
            file.write_all(&bytes).unwrap();
        }
        panic!(
            "seed={seed} {settings}: {details}; reproducer {}",
            directory.display()
        );
    }

    fn logical(profile: &ExecutionProfile) -> Vec<Vec<u64>> {
        profile
            .functions
            .iter()
            .map(|f| {
                let mut counts = f.interpreted.clone();
                for (pc, &hits) in f
                    .jit_blocks
                    .iter()
                    .enumerate()
                    .filter(|(_, hits)| **hits != 0)
                {
                    for count in &mut counts[pc..f.jit_block_ends[pc]] {
                        *count += hits;
                    }
                }
                counts
            })
            .collect()
    }

    #[test]
    fn generated_cfgs_match_interpreter_across_native_modes_and_budgets() {
        let setting = |name: &str, default: u64| {
            std::env::var(name)
                .map(|v| v.parse::<u64>().expect("integer differential setting"))
                .unwrap_or(default)
        };
        let start = setting("RUST_INTERP_DIFF_SEED", 0);
        let cases = setting("RUST_INTERP_DIFF_CASES", 32);
        assert!(
            (1..=4096).contains(&cases),
            "bounded differential case count required"
        );
        for index in 0..cases {
            let seed = start.wrapping_add(index);
            let p = program(seed);
            validate(&p).unwrap();
            let argument = (seed as u128) << 64 | 0xfedcba9876543210;
            let limits = |budget| Limits {
                instructions: budget,
                memory: 4 * 1024 * 1024,
                allocations: 64,
                frames: 8,
                ..Limits::default()
            };
            let (complete, reference) =
                execute_profiled(&p, &[argument], limits(100_000), Engine::Interpreter)
                    .unwrap_or_else(|error| fail(seed, &p, argument, "reference", error));
            let mut budgets = vec![
                0,
                1,
                17,
                complete.instructions / 2,
                complete.instructions - 1,
                complete.instructions,
            ];
            budgets.sort_unstable();
            budgets.dedup();
            for budget in budgets {
                let expected =
                    execute_with_engine(&p, &[argument], limits(budget), Engine::Interpreter);
                for persistent in [false, true] {
                    for capacity in [0, 256, 1024 * 1024] {
                        for profiled in [false, true] {
                            let settings = format!(
                                "budget={budget} persistent={persistent} capacity={capacity} profiled={profiled}"
                            );
                            let native = Limits {
                                jit_resumable_calls: true,
                                jit_persistent_registers: persistent,
                                jit_code_bytes: capacity,
                                ..limits(budget)
                            };
                            let (actual, profile) = if profiled {
                                match execute_profiled(&p, &[argument], native, Engine::Jit) {
                                    Ok((execution, profile)) => (Ok(execution), Some(profile)),
                                    Err(error) => (Err(error), None),
                                }
                            } else {
                                (
                                    execute_with_engine(&p, &[argument], native, Engine::Jit),
                                    None,
                                )
                            };
                            if result(&actual) != result(&expected) {
                                fail(
                                    seed,
                                    &p,
                                    argument,
                                    &settings,
                                    format!("expected {expected:?}, actual {actual:?}"),
                                );
                            }
                            if let Some(profile) = profile {
                                if logical(&profile) != logical(&reference) {
                                    fail(
                                        seed,
                                        &p,
                                        argument,
                                        &settings,
                                        "per-PC logical profile differs".into(),
                                    );
                                }
                            }
                            if budget == complete.instructions && capacity == 1024 * 1024 {
                                let actual = actual.unwrap();
                                if actual.jit_compiled_functions != 2
                                    || actual.jit_resumable_calls == 0
                                {
                                    fail(
                                        seed,
                                        &p,
                                        argument,
                                        &settings,
                                        format!("missing native coverage: {actual:?}"),
                                    );
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
