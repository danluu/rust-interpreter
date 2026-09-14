use super::*;
use crate::{Engine, ExecutionProfile, Limits, Slot, execute_profiled, execute_with_engine};

fn function(name: &str, code: Vec<Op>) -> Function {
    Function { name: name.into(), registers: 8, frame_size: 32, frame_align: 16,
        args: vec![Slot { offset: 0, size: 8 }], result: Slot { offset: 8, size: 8 }, code }
}

fn program(functions: Vec<Function>) -> Program {
    Program { version: crate::VERSION, target: "aarch64-apple-darwin".into(), entry: 0,
        data: vec![0; 16], statics: vec![], thread_locals: vec![], functions }
}

fn options() -> Limits {
    Limits { jit_resumable_calls: true, jit_demand_regions: true, ..Limits::default() }
}

fn counts(profile: &ExecutionProfile) -> Vec<Vec<u64>> {
    profile.functions.iter().map(|f| {
        let mut result = f.interpreted.clone();
        for (out, hits) in result.iter_mut().zip(&f.jit_scalar_hits) { *out += hits; }
        for (pc, hits) in f.jit_blocks.iter().enumerate() {
            if *hits != 0 {
                assert!(f.jit_block_ends[pc] > pc && f.jit_block_ends[pc] <= result.len());
                for out in &mut result[pc..f.jit_block_ends[pc]] { *out += hits; }
            }
        }
        result
    }).collect()
}

fn equivalent_error(a: &str, b: &str) -> bool {
    let memory = |s: &str| matches!(s, "JIT guest memory access failed" | "invalid guest memory access" | "write to read-only guest memory");
    a == b || (memory(a) && memory(b))
}

fn compare(p: &Program, args: &[u128], limits: Limits) {
    let mut interpreter = limits.clone();
    interpreter.jit_demand_regions = false;
    interpreter.jit_resumable_calls = false;
    interpreter.jit_persistent_registers = false;
    interpreter.jit_scalar_calls = false;
    let reference = execute_profiled(p, args, interpreter, Engine::Interpreter);
    for persistent in [false, true] { for scalar in [false, true] {
        let mut candidate = limits.clone();
        candidate.jit_persistent_registers = persistent;
        candidate.jit_scalar_calls = scalar;
        let mut eager = candidate.clone(); eager.jit_demand_regions = false;
        let eager = execute_profiled(p, args, eager, Engine::Jit);
        let actual = execute_profiled(p, args, candidate, Engine::Jit);
        match (&reference, &eager, actual) {
            (Ok((a, ap)), Ok((b, bp)), Ok((c, cp))) => {
                assert_eq!((a.value, a.instructions, a.peak_memory), (c.value, c.instructions, c.peak_memory));
                assert_eq!((b.value, b.instructions, b.peak_memory), (c.value, c.instructions, c.peak_memory));
                assert_eq!(counts(ap), counts(&cp));
                assert_eq!(counts(bp), counts(&cp));
                let interpreted: u64 = cp.functions.iter().flat_map(|f| &f.interpreted).sum();
                assert_eq!(c.instructions, c.jit_instructions + interpreted);
            }
            (Err(a), Err(b), Err(c)) => {
                assert!(equivalent_error(a, &c), "interpreter {a}; demand {c}");
                assert!(equivalent_error(b, &c), "eager {b}; demand {c}");
            }
            (a, b, c) => panic!("interpreter {a:?}; eager {b:?}; demand {c:?}"),
        }
    } }
}

fn loop_program() -> Program {
    program(vec![function("loop with cold tail", vec![
        Op::Local { dst: 0, offset: 0 }, Op::Load { dst: 1, address: 0, size: 8 },
        Op::Imm { dst: 2, value: 0 }, Op::Imm { dst: 3, value: 1 },
        Op::Switch { value: 1, cases: vec![(0, 10)], otherwise: 5 },
        Op::Binary { dst: 1, overflow: 4, op: Binary::Sub, a: 1, b: 3, bits: 64, signed: false },
        Op::Binary { dst: 2, overflow: 4, op: Binary::Add, a: 2, b: 3, bits: 64, signed: false },
        Op::Jump { target: 4 }, Op::Imm { dst: 7, value: 1337 }, Op::Trap { message: "cold tail".into() },
        Op::Local { dst: 5, offset: 8 }, Op::Store { address: 5, src: 2, size: 8 }, Op::Return,
    ])])
}

fn calls_program() -> Program {
    let mut root = function("two calls", vec![Op::Local { dst: 0, offset: 0 },
        Op::Call { function: 1, args: vec![0], destination: 0 },
        Op::Call { function: 1, args: vec![0], destination: 0 }, Op::Return]);
    root.result.offset = 0;
    let leaf = function("checked add", vec![Op::Local { dst: 0, offset: 0 },
        Op::Load { dst: 1, address: 0, size: 8 },
        Op::Assert { value: 1, expected: true, message: "argument must be nonzero".into() },
        Op::Imm { dst: 2, value: 1 },
        Op::Binary { dst: 3, overflow: 4, op: Binary::Add, a: 1, b: 2, bits: 64, signed: false },
        Op::Local { dst: 5, offset: 8 }, Op::Store { address: 5, src: 3, size: 8 }, Op::Return]);
    program(vec![root, leaf])
}

#[test]
fn live_demand_loops_preserve_counts_and_omit_cold_regions() {
    let p = loop_program();
    for input in [0, 1, 2, 7, 50] { compare(&p, &[input], options()); }
    let run = execute_with_engine(&p, &[7], options(), Engine::Jit).unwrap();
    let eager = execute_with_engine(&p, &[7], Limits { jit_demand_regions: false, ..options() }, Engine::Jit).unwrap();
    assert_eq!(run.value, 7);
    assert!(run.jit_operations < eager.jit_operations);
    assert!(run.jit_bytes < eager.jit_bytes);
    let demand = run.jit_demand.unwrap();
    assert!(eager.jit_demand.is_none());
    assert_eq!(demand.published_regions, 5);
    assert_eq!((demand.declined_regions, demand.eager_fallbacks), (0, 0));
    assert!((1..=MAX_RETAINED_BYTES).contains(&demand.plan_bytes));
    assert!((1..=MAX_METADATA_BYTES).contains(&demand.metadata_bytes));
}

#[test]
fn live_demand_budget_tails_and_guard_declines_do_not_retry_forever() {
    let p = loop_program();
    for instructions in 0..=30 { compare(&p, &[3], Limits { instructions, ..options() }); }
    let mut code = vec![Op::Local { dst: 0, offset: 0 }, Op::Load { dst: 1, address: 0, size: 8 }];
    code.extend(vec![Op::Load { dst: 2, address: 1, size: 8 }; 8]);
    code.extend([Op::Local { dst: 3, offset: 8 }, Op::Store { address: 3, src: 2, size: 8 }, Op::Return]);
    let p = program(vec![function("guard decline", code)]);
    for address in [0, 16, 40, u64::MAX as u128] {
        for instructions in 0..=14 { compare(&p, &[address], Limits { instructions, ..options() }); }
    }
}

#[test]
fn live_demand_calls_returns_and_scalar_composition_preserve_fault_order() {
    let p = calls_program();
    for input in [0, 1, 7] {
        for instructions in 0..=21 { compare(&p, &[input], Limits { instructions, ..options() }); }
    }
    for memory in [0, 32, 128, 256, 4096] { for frames in [1, 2, 3] {
        compare(&p, &[7], Limits { memory, frames, ..options() });
    } }
}

#[test]
fn prepared_demand_runs_keep_fresh_guest_state_and_fixed_codegen_options() {
    let p = calls_program();
    let limits = Limits { jit_persistent_registers: true, jit_scalar_calls: true, ..options() };
    let mut prepared = crate::PreparedJit::new(&p, &limits).unwrap();
    for input in [2, 0, 4, 0, 2] {
        let expected = execute_with_engine(&p, &[input], Limits {
            jit_resumable_calls: false, jit_persistent_registers: false,
            jit_scalar_calls: false, jit_demand_regions: false, ..limits.clone()
        }, Engine::Interpreter);
        let actual = prepared.execute(&[input], limits.clone());
        match (expected, actual) {
            (Ok(a), Ok(b)) => assert_eq!((a.value, a.instructions, a.peak_memory), (b.value, b.instructions, b.peak_memory)),
            (Err(a), Err(b)) => assert!(equivalent_error(&a, &b)),
            (a, b) => panic!("prepared reference {a:?}; demand {b:?}"),
        }
    }
    assert!(prepared.execute(&[2], Limits { jit_demand_regions: false, ..limits.clone() })
        .unwrap_err().contains("code-generation options changed"));
    assert_eq!(prepared.execute(&[2], limits.clone()).unwrap().value, 4);
    assert_eq!(prepared.execute_entry(1, &[9], limits).unwrap().value, 10);
}

#[test]
fn demand_admission_refusals_reuse_eager_analysis_and_code_limits_keep_vm_paths() {
    let p = loop_program();
    let mut eager = Jit::new_resumable(&p, false, MAX_CODE_BYTES, true).unwrap();
    eager.ensure_function(0).unwrap();
    let words = eager.code.as_ref().unwrap().published().1.to_vec();
    for metadata in [false, true] {
        let mut jit = Jit::new_resumable(&p, false, MAX_CODE_BYTES, true).unwrap();
        jit.enable_demand_regions().unwrap();
        let state = jit.demand.as_mut().unwrap();
        if metadata {
            // Simulate the remaining aggregate allowance being consumed by
            // other functions; no foreign process or real workload is involved.
            state.metadata_used = MAX_METADATA_BYTES;
        } else {
            let base = std::mem::size_of::<Plans>() + p.functions.len() * std::mem::size_of::<Option<Box<FunctionAnalysis>>>();
            state.plans = Box::new(Plans::new(p.functions.len(), base).unwrap());
        }
        jit.ensure_function(0).unwrap();
        assert_eq!(jit.demand.as_ref().unwrap().eager_fallbacks, 1);
        assert_eq!(jit.demand_statistics().unwrap().eager_fallbacks, 1);
        assert!(jit.demand.as_ref().unwrap().functions[0].is_none());
        assert_eq!(jit.code.as_ref().unwrap().published().1, words);
        assert!(!jit.wants_region(0, 4));
    }
    for jit_code_bytes in [0, 4, 64, 512, 1024] {
        compare(&p, &[3], Limits { jit_code_bytes, ..options() });
        let run = execute_with_engine(&p, &[3], Limits { jit_code_bytes, ..options() }, Engine::Jit).unwrap();
        assert!(run.jit_bytes <= jit_code_bytes);
        let stats = run.jit_demand.unwrap();
        if jit_code_bytes == 0 { assert_eq!(stats.published_regions, 0); assert!(stats.declined_regions > 0); }
    }
}

#[test]
fn demand_mode_requires_explicit_checked_resumable_configuration() {
    let p = loop_program();
    for (engine, limits) in [(Engine::Interpreter, Limits { jit_demand_regions: true, ..Limits::default() }),
        (Engine::Jit, Limits { jit_demand_regions: true, ..Limits::default() })] {
        assert!(execute_with_engine(&p, &[1], limits, engine).unwrap_err()
            .contains("fully validated resumable JIT"));
    }
    let mut partial = p.clone(); partial.version |= crate::PARTIAL_VALIDATION;
    assert!(execute_with_engine(&partial, &[1], options(), Engine::Jit).unwrap_err()
        .contains("fully validated resumable JIT"));
}

#[test]
fn demand_maps_cover_mixed_eager_fallback_and_reject_corrupt_receipts() {
    let mut p = loop_program();
    p.functions.push(p.functions[0].clone());
    let mut jit = Jit::new_resumable(&p, true, MAX_CODE_BYTES, true).unwrap();
    jit.enable_demand_regions().unwrap();
    jit.ensure_function(0).unwrap();
    for pc in [10, 4, 5, 12] { jit.ensure_region(0, pc).unwrap(); }
    jit.demand.as_mut().unwrap().metadata_used = MAX_METADATA_BYTES;
    jit.ensure_function(1).unwrap();
    assert_eq!(jit.demand.as_ref().unwrap().eager_fallbacks, 1);
    let map = serde_json::to_value(jit.operation_map().unwrap()).unwrap();
    let rows = map["functions"].as_array().unwrap();
    assert!(rows.iter().filter(|r| r["function"] == 0).all(|r| r["region_pc"].is_number()));
    assert_eq!(rows.iter().filter(|r| r["function"] == 1).count(), 1);
    assert!(rows.last().unwrap().get("region_pc").is_none());
    for corruption in 0..6 {
        let state = jit.demand.as_mut().unwrap().functions[0].as_mut().unwrap();
        let duplicate_pc = state.publications[1].pc;
        let publication = &mut state.publications[0];
        let old = (publication.pc, publication.offset, publication.bytes, publication.assertion_base, publication.assertions);
        match corruption {
            0 => publication.pc = usize::MAX,
            1 => publication.offset += 4,
            2 => publication.bytes += 4,
            3 => publication.assertion_base += 1,
            4 => publication.assertions += 1,
            5 => publication.pc = duplicate_pc,
            _ => unreachable!(),
        }
        assert!(jit.operation_map().is_err(), "corrupt receipt {corruption}");
        let publication = &mut jit.demand.as_mut().unwrap().functions[0].as_mut().unwrap().publications[0];
        (publication.pc, publication.offset, publication.bytes, publication.assertion_base, publication.assertions) = old;
        jit.operation_map().unwrap();
    }
    // The cold trap has a reserved zero resume slot but no code publication.
    *jit.resumable.as_mut().unwrap().vacant_entry(0, 8).unwrap() = 4;
    assert!(jit.operation_map().is_err());
}

#[test]
fn live_demand_dumps_match_executed_code_and_preserve_profiles() {
    static NEXT: std::sync::atomic::AtomicUsize = std::sync::atomic::AtomicUsize::new(0);
    let root = std::env::temp_dir().join(format!("rust-interp-demand-map-{}-{}", std::process::id(),
        NEXT.fetch_add(1, std::sync::atomic::Ordering::Relaxed)));
    std::fs::create_dir(&root).unwrap();
    for (case, p) in [loop_program(), calls_program()].into_iter().enumerate() {
        for persistent in [false, true] { for scalar in [false, true] {
            let limits = Limits { jit_persistent_registers: persistent, jit_scalar_calls: scalar, ..options() };
            let (expected, expected_profile) = execute_profiled(&p, &[7], limits.clone(), Engine::Jit).unwrap();
            let path = root.join(format!("{case}-{persistent}-{scalar}"));
            let (actual, profile) = execute_profiled(&p, &[7], Limits { jit_code_dump: Some(path.clone()),
                jit_operation_map: true, ..limits }, Engine::Jit).unwrap();
            assert_eq!((actual.value, actual.instructions, actual.peak_memory, actual.jit_bytes),
                (expected.value, expected.instructions, expected.peak_memory, expected.jit_bytes));
            assert_eq!(counts(&profile), counts(&expected_profile));
            let load = |name| serde_json::from_slice::<serde_json::Value>(&std::fs::read(path.join(name)).unwrap()).unwrap();
            let operations = load("operations.json"); let ranges = load("map.json");
            assert_eq!(operations["schema_version"], 3); assert_eq!(ranges["schema_version"], 2);
            assert_eq!(operations["demand_regions"], true); assert_eq!(ranges["demand_regions"], true);
            assert_eq!(operations["code_bytes"], actual.jit_bytes);
            assert_eq!(operations["arena_base"], ranges["arena_base"]);
            assert_eq!(operations["reconstructed_bytes_match"], true);
            use sha2::Digest;
            assert_eq!(operations["code_sha256"], format!("{:x}", sha2::Sha256::digest(std::fs::read(path.join("code.bin")).unwrap())));
            assert!(operations["functions"].as_array().unwrap().iter().any(|r| r["region_pc"].is_number()));
        } }
    }
    std::fs::remove_dir_all(root).unwrap();
}

#[test]
fn live_demand_tls_callbacks_nested_calls_and_reset_keep_exact_accounting() {
    let mut code = vec![Op::ResetThreadLocals];
    for argument in [1, 2] {
        code.extend([Op::Imm { dst: 0, value: (crate::FUNCTION_POINTER_TAG | 2) as u128 },
            Op::Imm { dst: 1, value: argument }, Op::RegisterTlsDestructor { callback: 0, argument: 1 }]);
    }
    code.extend([Op::ResetThreadLocals,
        Op::Imm { dst: 0, value: (crate::HEAP_POINTER_TAG + 16) as u128 },
        Op::Load { dst: 1, address: 0, size: 8 },
        Op::Assert { value: 1, expected: false, message: "TLS reset after callbacks".into() },
        Op::Imm { dst: 0, value: (crate::HEAP_POINTER_TAG + 32) as u128 },
        Op::Local { dst: 1, offset: 8 }, Op::Copy { dst: 1, src: 0, size: 8 }, Op::Return]);
    let mut root = function("TLS root", code); root.args.clear();
    let mut callback = function("TLS callback", vec![Op::Local { dst: 0, offset: 0 },
        Op::Load { dst: 1, address: 0, size: 8 },
        Op::Imm { dst: 2, value: (crate::HEAP_POINTER_TAG + 32) as u128 },
        Op::Load { dst: 3, address: 2, size: 8 }, Op::Imm { dst: 4, value: 10 },
        Op::Binary { dst: 3, overflow: 7, op: Binary::Mul, a: 3, b: 4, bits: 64, signed: false },
        Op::Binary { dst: 3, overflow: 7, op: Binary::Add, a: 3, b: 1, bits: 64, signed: false },
        Op::Store { address: 2, src: 3, size: 8 },
        Op::Imm { dst: 2, value: (crate::HEAP_POINTER_TAG + 16) as u128 },
        Op::Store { address: 2, src: 1, size: 8 }, Op::Return]);
    callback.result.size = 0;
    for nested in [false, true] {
        let mut p = program(vec![root.clone(), callback.clone()]);
        p.statics = vec![0; 48]; p.thread_locals = vec![Slot { offset: 16, size: 8 }];
        if nested {
            let mut child = callback.clone(); child.name = "nested TLS helper".into();
            p.functions.push(child);
            p.functions[1].code = vec![Op::Local { dst: 0, offset: 0 },
                Op::Call { function: 2, args: vec![0], destination: 0 }, Op::Return];
        }
        let reference = execute_with_engine(&p, &[], Limits::default(), Engine::Interpreter).unwrap();
        assert_eq!(reference.value, 21);
        for instructions in 0..=reference.instructions + 1 { compare(&p, &[], Limits { instructions, ..options() }); }
    }
}
