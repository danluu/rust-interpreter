use super::*;
use crate::PreparedJit;

const CALL_PC: usize = 8;

fn handle(id: usize) -> u128 {
    (crate::FUNCTION_POINTER_TAG | (id as u64 + 1)) as u128
}

fn fixture(registers: usize) -> Program {
    let target = registers as Reg - 1;
    let mut caller = function(vec![
        Op::Local { dst: 0, offset: 0 },
        Op::Load { dst: target, address: 0, size: 16 },
        Op::Local { dst: 1, offset: 16 },
        Op::Imm { dst: 2, value: 5 },
        Op::Store { address: 1, src: 2, size: 8 },
        Op::Imm { dst: 3, value: 0 },
        Op::Imm { dst: 4, value: 4 },
        Op::Imm { dst: 5, value: 1 },
        Op::CallIndirect { callee: target, args: vec![1], arg_sizes: vec![8], destination: 1, result_size: 8 },
        binary(3, Binary::Add, 3, 5),
        binary(6, Binary::Lt, 3, 4),
        Op::Switch { value: 6, cases: vec![(1, CALL_PC)], otherwise: 12 },
        Op::Load { dst: 2, address: 1, size: 8 },
        Op::Store { address: 0, src: 2, size: 8 },
        Op::Return,
    ]);
    caller.registers = registers;
    caller.args = vec![Slot { offset: 0, size: 16 }];
    let mut children = vec![];
    for add in [1u128, 2, 3] {
        let mut child = function(vec![
            Op::Local { dst: 0, offset: 0 },
            Op::Load { dst: 1, address: 0, size: 8 },
            Op::Imm { dst: 2, value: add },
            binary(1, Binary::Add, 1, 6), // Initial zero must survive reuse.
            Op::Imm { dst: 6, value: 99 }, // Dirty the same retained register.
            binary(1, Binary::Add, 1, 2),
            Op::Store { address: 0, src: 1, size: 8 },
            Op::Return,
        ]);
        child.args = vec![Slot { offset: 0, size: if add == 3 { 16 } else { 8 } }];
        children.push(child);
    }
    program([vec![caller], children].concat())
}

fn limits(persistent: bool, capacity: usize) -> Limits {
    Limits { jit_resumable_calls: true, jit_persistent_registers: persistent,
        jit_code_bytes: capacity, ..Limits::default() }
}

#[test]
fn guarded_calls_match_native_arithmetic_and_exact_profiles_at_far_registers() {
    for registers in [16, 2052] {
        let p = fixture(registers);
        assert!(crate::registers::needs_initial_zeroes(&p.functions[1]));
        for id in [1, 2] {
            let args = [handle(id)];
            let (expected, reference) = execute_profiled(&p, &args, Limits::default(), Engine::Interpreter).unwrap();
            assert_eq!(expected.value, 5 + 4 * id as u128); // Independent Rust arithmetic.
            for persistent in [false, true] {
                let (actual, profile) = execute_profiled(&p, &args, limits(persistent, MAX_CODE_BYTES), Engine::Jit).unwrap();
                assert_eq!((actual.value, actual.instructions, actual.peak_memory),
                    (expected.value, expected.instructions, expected.peak_memory));
                assert_eq!(logical(&profile), logical(&reference));
                assert_eq!(profile.functions[0].interpreted[CALL_PC], 1);
                assert_eq!(actual.jit_resumable_calls, 3);
                assert_eq!(actual.jit_resumable_returns, 4);
            }
        }
    }
}

#[test]
fn prepared_indirect_guards_recheck_targets_and_full_handles_with_fresh_state() {
    for persistent in [false, true] {
        let p = fixture(2052);
        let options = || limits(persistent, MAX_CODE_BYTES);
        let mut prepared = PreparedJit::new(&p, &options()).unwrap();
        let mut stable_bytes = 0;
        for (index, id) in [1usize, 2, 1, 2, 1].into_iter().enumerate() {
            let actual = prepared.execute(&[handle(id)], options()).unwrap();
            assert_eq!(actual.value, 5 + 4 * id as u128);
            assert_eq!(actual.jit_resumable_calls, if id == 2 { 0 } else if index == 0 { 3 } else { 4 });
            if index == 1 { stable_bytes = actual.jit_bytes; }
            if index > 1 {
                assert_eq!(actual.jit_bytes, stable_bytes);
                assert_eq!(actual.jit_compile_nanos, 0);
            }
        }
        for bad in [0, crate::FUNCTION_POINTER_TAG as u128, handle(999_999),
                    handle(1) | (1u128 << 100), handle(3)] {
            let expected = execute_with_engine(&p, &[bad], Limits::default(), Engine::Interpreter);
            assert!(expected.is_err());
            equal_result(prepared.execute(&[bad], options()), &expected);
            let restored = prepared.execute(&[handle(1)], options()).unwrap();
            assert_eq!(restored.value, 9);
            assert_eq!(restored.jit_resumable_calls, 4);
            assert_eq!(restored.jit_bytes, stable_bytes);
        }
    }
}

#[test]
fn indirect_budget_tails_and_independent_memory_depth_limits_match_interpretation() {
    for registers in [16, 2052] {
        let p = fixture(registers);
        let args = [handle(1)];
        let reference = execute_with_engine(&p, &args, Limits::default(), Engine::Interpreter).unwrap();
        for persistent in [false, true] {
            for capacity in [0, MAX_CODE_BYTES] {
                for instructions in 0..=reference.instructions + 1 {
                    let expected = execute_with_engine(&p, &args, Limits { instructions, ..Limits::default() }, Engine::Interpreter);
                    equal_result(execute_with_engine(&p, &args, Limits { instructions, ..limits(persistent, capacity) }, Engine::Jit), &expected);
                }
                let working = (registers + 8) * 16 + 80;
                for memory in [working - 1, working, working + 1] {
                    let expected = execute_with_engine(&p, &args, Limits { memory, ..Limits::default() }, Engine::Interpreter);
                    equal_result(execute_with_engine(&p, &args, Limits { memory, ..limits(persistent, capacity) }, Engine::Jit), &expected);
                }
                for frames in [1, 2, 3] {
                    let expected = execute_with_engine(&p, &args, Limits { frames, ..Limits::default() }, Engine::Interpreter);
                    equal_result(execute_with_engine(&p, &args, Limits { frames, ..limits(persistent, capacity) }, Engine::Jit), &expected);
                }
            }
        }
    }
}

#[test]
fn indirect_publication_is_bounded_and_never_retargets_or_partially_publishes() {
    let p = fixture(16);
    let mut jit = Jit::new_resumable(&p, false, MAX_CODE_BYTES, true).unwrap();
    for id in [0, 1, 2] { jit.ensure_function(id).unwrap(); }
    let static_bytes = jit.bytes;
    assert!(!jit.prepare_indirect(0, CALL_PC, 3).unwrap()); // Signature mismatch.
    assert!(!jit.resumable.as_ref().unwrap().indirect[0].attempted[CALL_PC]);
    assert!(jit.prepare_indirect(0, CALL_PC, 1).unwrap());
    let bytes = jit.bytes;
    let entry = jit.resumable.as_ref().unwrap().indirect[0].entries[CALL_PC];
    assert!(entry != 0 && bytes > static_bytes);
    for target in [1, 2, 1] {
        assert!(!jit.prepare_indirect(0, CALL_PC, target).unwrap());
        assert_eq!(jit.bytes, bytes);
        assert_eq!(jit.resumable.as_ref().unwrap().indirect[0].entries[CALL_PC], entry);
    }
    // Appended thunks must not be attributed to the preceding native region.
    let dump = std::env::temp_dir().join(format!("rust-interp-indirect-map-{}-{}",
        std::process::id(), std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_nanos()));
    jit.dump_code(&dump).unwrap();
    let map: serde_json::Value = serde_json::from_slice(&std::fs::read(dump.join("map.json")).unwrap()).unwrap();
    let ranges = map["ranges"].as_array().unwrap();
    let thunk = ranges.iter().find(|r| r["kind"] == "resumable_indirect_call").unwrap();
    assert_eq!(thunk["function"], 0);
    assert_eq!(thunk["pc"], CALL_PC);
    assert_eq!(thunk["offset"], static_bytes);
    assert_eq!(thunk["end"], bytes);
    assert_eq!(ranges.last().unwrap()["end"], map["code_bytes"]);
    std::fs::remove_dir_all(dump).unwrap();
    for capacity in [0, static_bytes] {
        let mut full = Jit::new_resumable(&p, false, capacity, true).unwrap();
        for id in [0, 1, 2] { full.ensure_function(id).unwrap(); }
        let before = full.bytes;
        assert!(!full.prepare_indirect(0, CALL_PC, 1).unwrap());
        assert_eq!(full.bytes, before);
        assert!(full.resumable.as_ref().unwrap().indirect[0].entries.iter().all(|&p| p == 0));
    }
    let tables = Entries::new(&p);
    let maximum = (MAX_ENTRY_BYTES - 8) / 17;
    assert!(tables.fits(maximum, true));
    assert!(!tables.fits(maximum + 1, true));
}

#[test]
fn unready_indirect_targets_decline_until_the_existing_vm_prepares_them() {
    let p = fixture(16);
    let options = || limits(true, MAX_CODE_BYTES);
    let mut jit = Some(Jit::new_resumable(&p, false, MAX_CODE_BYTES, true).unwrap());
    jit.as_mut().unwrap().ensure_function(0).unwrap();
    assert!(jit.as_mut().unwrap().prepare_indirect(0, CALL_PC, 1).unwrap());
    assert!(jit.as_ref().unwrap().resumable.as_ref().unwrap().pointers[1].is_null());
    let metadata = crate::ExecutionMetadata::new(&p, jit.as_ref(), true);
    let actual = crate::execute_prepared_impl::<false, true, false, false, true>(
        &p, 0, &[handle(1)], options(), None, &mut jit, &metadata).unwrap();
    assert_eq!(actual.value, 9);
    assert_eq!(actual.jit_resumable_calls, 3);
    assert!(!jit.as_ref().unwrap().resumable.as_ref().unwrap().pointers[1].is_null());
}
