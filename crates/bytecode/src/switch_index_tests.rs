use super::*;
use crate::{Engine, Function, Limits, Slot, VERSION};

fn reference(cases: &Cases, value: u128, otherwise: usize) -> usize {
    for &(key, target) in cases { if key == value { return target; } }
    otherwise
}

#[test]
fn dense_sparse_duplicates_and_full_width_match_first_case_oracle() {
    for seed in 0..160u128 {
        for wide in [false, true] {
            let cases: Vec<_> = (0..MIN_CASES + seed as usize % 65).map(|i| {
                let low = ((i as u128 * 67) ^ seed) % 101;
                let key = if wide { low << 100 | seed } else { low + 1000 };
                (key, i + 200)
            }).rev().collect();
            let index = Index::build(&cases, MAX_BYTES).unwrap();
            assert_eq!(matches!(index, Index::Sorted(_)), wide);
            for key in cases.iter().map(|r| r.0).chain([0, 999, 1101, 1 << 64, u128::MAX]) {
                assert_eq!(index.target(&cases, key, 99), reference(&cases, key, 99));
            }
        }
    }
    let mut cases: Vec<_> = (0..32).map(|i| (u128::MAX - i, i as usize)).collect();
    cases.push((u128::MAX, 999));
    let index = Index::build(&cases, MAX_BYTES).unwrap();
    assert!(matches!(index, Index::Dense { .. }));
    assert_eq!(index.target(&cases, u128::MAX, 88), 0);
    assert_eq!(index.target(&cases, u128::MAX - 40, 88), 88);
    cases.push((0, 444));
    let index = Index::build(&cases, MAX_BYTES).unwrap();
    assert!(matches!(index, Index::Sorted(_)));
    assert_eq!(index.target(&cases, 0, 88), 444);
}

fn function(cases: Vec<(u128, usize)>) -> Function {
    Function { name: "switch-index-control".into(), frame_size: 32, frame_align: 16, registers: 2,
        args: vec![Slot { offset: 0, size: 16 }], result: Slot { offset: 16, size: 16 },
        code: vec![Op::Local { dst: 1, offset: 0 }, Op::Load { dst: 0, address: 1, size: 16 },
            Op::Local { dst: 1, offset: 16 }, Op::Switch { value: 0, cases, otherwise: 10 },
            Op::Imm { dst: 0, value: 11 }, Op::Store { address: 1, src: 0, size: 16 }, Op::Return,
            Op::Imm { dst: 0, value: 22 }, Op::Store { address: 1, src: 0, size: 16 }, Op::Return,
            Op::Imm { dst: 0, value: 33 }, Op::Store { address: 1, src: 0, size: 16 }, Op::Return] }
}
fn program(functions: Vec<Function>) -> Program {
    Program { version: VERSION, target: "aarch64-apple-darwin".into(), entry: 0, functions,
        data: vec![], statics: vec![], thread_locals: vec![] }
}

#[test]
fn resource_refusals_and_cache_capacity_preserve_linear_semantics() {
    let cases: Vec<_> = (0..32).map(|i| (i, 4)).collect();
    assert!(Index::build(&cases, 0).is_none());
    assert!(Index::build(&cases[..31], MAX_BYTES).is_none());
    assert!(Index::build(&vec![(1, 4); MAX_CASES + 1], MAX_BYTES).is_none());
    let p = program((0..MAX_ENTRIES + 5).map(|_| function(cases.clone())).collect());
    let mut cache = Cache::new(&p);
    assert!(cache.entries.is_empty() && cache.entries.capacity() == 0);
    for id in (0..p.functions.len()).rev() {
        assert_eq!(cache.target(id, 3, 0), 4);
        assert_eq!(cache.target(id, 3, u128::MAX), 10);
    }
    assert_eq!(cache.entries.len(), MAX_ENTRIES);
    assert!(cache.table_bytes + cache.entries.capacity() * std::mem::size_of::<Entry>() <= MAX_BYTES);
    // Exhaust the aggregate table budget before the entry limit.
    let large: Vec<_> = (0..4096).map(|i| ((i as u128) << 100, 4)).collect();
    let p = program((0..40).map(|_| function(large.clone())).collect());
    let mut cache = Cache::new(&p);
    for id in 0..40 { assert_eq!(cache.target(id, 3, 123 << 100), 4); }
    assert!(cache.entries.iter().any(|e| matches!(e.index, Index::Linear)));
    assert!(cache.table_bytes + cache.entries.capacity() * std::mem::size_of::<Entry>() <= MAX_BYTES);
    let before = cache.table_bytes;
    assert_eq!(cache.target(39, 3, 1), 10);
    assert_eq!(cache.table_bytes, before);
}

#[test]
fn execution_budget_profile_and_validation_match_without_indices() {
    let mut cases: Vec<_> = (0..40).rev().map(|i| ((i as u128) << 100, 4)).collect();
    cases.insert(0, (7 << 100, 7)); // duplicate must prefer this original case
    let p = program(vec![function(cases)]);
    for engine in [Engine::Interpreter, Engine::Jit] {
        for value in [0, 7 << 100, u128::MAX] {
            for budget in 0..12 {
                let limits = Limits { instructions: budget, ..Limits::default() };
                let baseline = crate::execute_with_engine(&p, &[value], limits.clone(), engine);
                let candidate = crate::execute_with_engine(&p, &[value], Limits { indexed_switches: true, ..limits }, engine);
                match (baseline, candidate) {
                    (Ok(a), Ok(b)) => {
                        assert_eq!((a.value, a.instructions, a.peak_memory), (b.value, b.instructions, b.peak_memory));
                        assert_eq!((a.jit_bytes, a.jit_instructions), (b.jit_bytes, b.jit_instructions));
                    }
                    (Err(a), Err(b)) => assert_eq!(a, b),
                    _ => panic!("index changed success/failure"),
                }
            }
        }
    }
    for engine in [Engine::Interpreter, Engine::Jit] {
        let (_, a) = crate::execute_profiled(&p, &[7 << 100], Limits::default(), engine).unwrap();
        let (_, b) = crate::execute_profiled(&p, &[7 << 100], Limits { indexed_switches: true, ..Limits::default() }, engine).unwrap();
        assert_eq!(serde_json::to_value(a).unwrap(), serde_json::to_value(b).unwrap());
    }
    let mut partial = p.clone(); partial.version |= crate::PARTIAL_VALIDATION;
    assert!(crate::execute_with_engine(&partial, &[0], Limits { indexed_switches: true, ..Limits::default() },
        Engine::Interpreter).unwrap_err().contains("full validation"));
    let mut invalid = p; invalid.functions.push(function(vec![(0, usize::MAX); 40]));
    assert!(crate::execute_with_engine(&invalid, &[0], Limits { indexed_switches: true, ..Limits::default() }, Engine::Interpreter).is_err());
}

#[test]
fn prepared_invocations_keep_indices_local_and_match_alternate_entries() {
    let p = program(vec![function((0..40).map(|i| (i, 4)).collect()),
        function((0..40).rev().map(|i| (i, 7)).collect())]);
    let enabled = Limits { indexed_switches: true, jit_resumable_calls: true, jit_persistent_registers: true, ..Limits::default() };
    let mut prepared = crate::PreparedJit::new(&p, &enabled).unwrap();
    for (entry, value, expected) in [(0, 2, 11), (1, 2, 22), (0, u128::MAX, 33), (1, 0, 22)] {
        assert!(prepared.execute_entry(entry, &[value], Limits { instructions: 3, ..enabled.clone() }).is_err());
        for indexed_switches in [false, true] {
            let actual = prepared.execute_entry(entry, &[value], Limits { indexed_switches, ..enabled.clone() }).unwrap();
            assert_eq!(actual.value, expected);
        }
    }
}
