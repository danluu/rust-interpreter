use super::*;
use crate::{ExecutionMetadata, Function, Limits, Op, Program, Slot, VERSION};

fn snapshot() -> Snapshot {
    Snapshot::from_pairs([
        (b"KEY".to_vec(), b"first".to_vec()),
        (b"EMPTY".to_vec(), vec![]),
        (b"KEY".to_vec(), b"second".to_vec()),
        (vec![0xff], vec![0x80, b'=', 0xfe]),
        (b"invalid=name".to_vec(), b"ignored".to_vec()),
        (vec![], b"ignored".to_vec()),
    ], 4096).unwrap()
}

fn memory(name: &[u8], limit: usize) -> Memory {
    let mut bytes = vec![0; 64];
    bytes[16..16 + name.len()].copy_from_slice(name);
    Memory { bytes: bytes.into(), heap: crate::heap::Heap::default(), limit,
        readonly_end: 64, peak: 0, auxiliary_bytes: 0 }
}

#[test]
fn absent_empty_raw_bytes_and_duplicate_names_match_c_lookup() {
    let snapshot = snapshot();
    for (name, expected) in [(&b"KEY"[..], Some(&b"first\0"[..])),
        (&b"EMPTY"[..], Some(&b"\0"[..])), (&b"missing"[..], None),
        (&b""[..], None), (&b"invalid=name"[..], None),
        (&[0xff][..], Some(&[0x80, b'=', 0xfe, 0][..]))] {
        let mut m = memory(name, 4096);
        let base = snapshot.install(&mut m).unwrap();
        let pointer = snapshot.get(&m, base, 16).unwrap();
        assert_eq!(pointer, snapshot.get(&m, base, 16).unwrap());
        match expected {
            Some(value) => {
                assert_ne!(pointer, 0);
                assert_eq!(m.read(pointer as usize, value.len()).unwrap(), value);
            }
            None => assert_eq!(pointer, 0),
        }
    }
}

#[test]
fn imported_values_are_readonly_unowned_and_stable_across_frames() {
    let snapshot = snapshot();
    let mut m = memory(b"KEY", 4096);
    let base = snapshot.install(&mut m).unwrap();
    let pointer = snapshot.get(&m, base, 16).unwrap() as usize;
    assert_eq!(m.store(pointer, 1, 17).unwrap_err(), "write to read-only guest memory");
    assert!(m.heap.deallocate(pointer, 6, 1).is_err());
    let frame = m.reserve_frame(128, 64).unwrap();
    m.store(frame, 8, 99).unwrap();
    m.bytes.truncate(frame);
    m.reserve_frame(256, 128).unwrap();
    assert_eq!(m.read(pointer, 6).unwrap(), b"first\0");
    let name = m.heap.allocate(4, 1, 1024, true).unwrap();
    for (index, &byte) in b"KEY\0".iter().enumerate() { m.store(name + index, 1, byte as u128).unwrap(); }
    assert_eq!(snapshot.get(&m, base, name as u128).unwrap(), pointer as u128);
    m.heap.deallocate(name, 4, 1).unwrap();
    assert_eq!(snapshot.get(&m, base, 16).unwrap(), pointer as u128);
}

#[test]
fn names_require_valid_nonnull_terminated_guest_storage() {
    let snapshot = snapshot();
    let mut m = memory(b"KEY", 4096);
    let base = snapshot.install(&mut m).unwrap();
    for pointer in [0, u128::MAX, m.bytes.len() as u128, crate::heap::TAG as u128] {
        assert!(snapshot.get(&m, base, pointer).is_err());
    }
    let frame = m.reserve_frame(8, 1).unwrap();
    m.bytes[frame..].fill(1);
    assert_eq!(snapshot.get(&m, base, frame as u128).unwrap_err(), "unterminated guest environment name");
}

#[test]
fn snapshot_and_install_admission_charge_bytes_and_index_without_partial_install() {
    let pair = || [(b"A".to_vec(), b"B".to_vec())];
    let charge = ENTRY_CHARGE + 1 + 2;
    assert!(Snapshot::from_pairs(pair(), charge - 1).is_err());
    let snapshot = Snapshot::from_pairs(pair(), charge).unwrap();
    let mut m = memory(b"A", 64 + charge - 1);
    let before = m.bytes.to_vec();
    assert!(snapshot.install(&mut m).is_err());
    assert_eq!(&*m.bytes, before);
    assert_eq!(m.auxiliary_bytes, 0);
    assert_eq!(m.readonly_end, 64);
    m.limit += 1;
    snapshot.install(&mut m).unwrap();
    assert_eq!(m.total_len(), 64 + charge);
    assert!(m.reserve_frame(1, 1).is_err());
    m.auxiliary_bytes = usize::MAX;
    assert!(snapshot.install(&mut m).is_err());
    for pair in [(b"A\0".to_vec(), vec![]), (b"A".to_vec(), b"B\0".to_vec())] {
        assert!(Snapshot::from_pairs([pair], 4096).is_err());
    }
}

fn program(write_value: bool) -> Program {
    let mut data = vec![0; 16]; data.extend_from_slice(b"KEY\0");
    let mut code = vec![Op::Imm { dst: 0, value: 16 }, Op::EnvironmentGet { dst: 0, name: 0 }];
    if write_value {
        code.extend([Op::Imm { dst: 1, value: 17 }, Op::Store { address: 0, src: 1, size: 1 }]);
    }
    code.extend([Op::Load { dst: 1, address: 0, size: 1 }, Op::Local { dst: 2, offset: 0 },
        Op::Store { address: 2, src: 1, size: 8 }, Op::Return]);
    Program { version: VERSION, data, statics: vec![], thread_locals: vec![], entry: 0,
        functions: vec![Function { name: "environment".into(), frame_size: 16, frame_align: 16,
            registers: 3, args: vec![], result: Slot { offset: 0, size: 8 }, code }] }
}

fn exercise<const JIT: bool, const RESUMABLE: bool>(p: &Program, persistent: bool) {
    crate::validate(p).unwrap();
    let settings = Limits { jit_persistent_registers: persistent, jit_resumable_calls: RESUMABLE, ..Limits::default() };
    let mut jit = crate::create_jit::<false, JIT, false, RESUMABLE>(p, &settings).unwrap();
    let metadata = ExecutionMetadata {
        needs_register_zeroes: p.functions.iter().map(crate::registers::needs_initial_zeroes).collect(),
        local_call_arguments: crate::calls::local_arguments(p), environment: Some(snapshot()),
    };
    for _ in 0..2 { // Same prepared code and input snapshot; fresh guest memory.
        for budget in 0..=p.functions[0].code.len() as u64 + 1 {
            let limits = Limits { instructions: budget, jit_persistent_registers: persistent,
                jit_resumable_calls: RESUMABLE, ..Limits::default() };
            let result = crate::execute_prepared_impl::<false, JIT, false, false, RESUMABLE>(
                p, 0, &[], limits, None, &mut jit, &metadata);
            if p.functions[0].code.len() == 6 && budget >= 6 {
                let result = result.unwrap(); assert_eq!(result.value, b'f' as u128); assert_eq!(result.instructions, 6);
            } else if let Err(error) = result {
                assert!(error.contains("instruction limit") || error == "write to read-only guest memory"
                    || (JIT && error == "JIT guest memory access failed"), "{error}");
            } else { panic!("unexpected successful execution"); }
        }
    }
}

#[test]
fn aliased_getenv_operand_budgets_and_readonly_faults_cross_all_engine_boundaries() {
    for write in [false, true] {
        let p = program(write);
        exercise::<false, false>(&p, false);
        for persistent in [false, true] {
            exercise::<true, false>(&p, persistent);
            exercise::<true, true>(&p, persistent);
        }
    }
}
