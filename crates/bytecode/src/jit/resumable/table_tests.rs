use super::*;

fn input() -> Program {
    Program { version: crate::VERSION, target: "aarch64-apple-darwin".into(), entry: 0,
        data: vec![0; 16], statics: vec![], thread_locals: vec![],
        functions: (0..3).map(|id| Function { name: format!("table_{id}"), frame_size: 16,
            frame_align: 16, registers: 1, args: vec![], result: crate::Slot { offset: 0, size: 0 },
            code: vec![Op::Imm { dst: 0, value: 1 }, Op::Return] }).collect() }
}

#[test]
fn filling_individual_resume_slots_preserves_table_and_pointer_array_addresses() {
    let p = input(); crate::validate(&p).unwrap();
    let mut tables = Entries::new(&p);
    let pointers = tables.pointers.as_ptr();
    assert!(tables.reserve_empty(1, 2).unwrap());
    let address = tables.pointers[1];
    assert!(!address.is_null());
    assert_eq!(tables.published(1), [0, 0, 0]);
    // Aligned synthetic values check metadata only; they are never executed.
    *tables.vacant_entry(1, 1).unwrap() = 0x4000;
    assert_eq!(tables.published(1), [0, 0x4000, 0]);
    assert!(tables.reserve_empty(0, 2).unwrap());
    assert!(tables.reserve_empty(2, 2).unwrap());
    *tables.vacant_entry(1, 0).unwrap() = 0x8000;
    assert_eq!(tables.pointers.as_ptr(), pointers);
    assert_eq!(tables.pointers[1], address);
    assert_eq!(tables.published(1), [0x8000, 0x4000, 0]);
    assert_eq!(tables.bytes, 9 * std::mem::size_of::<usize>());
    let before = tables.published(1).to_vec();
    for pc in [0, 1, 2, 3, usize::MAX] { assert!(tables.vacant_entry(1, pc).is_err()); }
    assert!(tables.vacant_entry(usize::MAX, 0).is_err());
    assert!(tables.reserve_empty(1, 2).is_err());
    assert_eq!(tables.published(1), before);
    assert_eq!(tables.pointers[1], address);
}

#[test]
fn resume_table_capacity_refusal_does_not_publish_a_pointer_or_consume_charge() {
    let p = input();
    let mut tables = Entries::new(&p);
    assert!(tables.reserve_empty(0, 0).is_err());
    assert!(tables.reserve_empty(usize::MAX, 1).is_err());
    assert!(!tables.reserve_empty(0, usize::MAX).unwrap());
    assert_eq!(tables.bytes, 0);
    assert!(tables.pointers.iter().all(|p| p.is_null()));
    // Allocate a real table leaving exactly three slots in the existing
    // aggregate budget; no guest program uses this oversized fixture table.
    assert!(tables.reserve_empty(0, MAX_ENTRY_BYTES / 8 - 4).unwrap());
    let address = tables.pointers[0];
    assert_eq!(tables.bytes, MAX_ENTRY_BYTES - 24);
    assert!(!tables.reserve_empty(1, 3).unwrap());
    assert!(tables.pointers[1].is_null() && tables.owned[1].is_empty());
    assert_eq!(tables.bytes, MAX_ENTRY_BYTES - 24);
    assert!(tables.reserve_empty(1, 2).unwrap());
    assert_eq!(tables.bytes, MAX_ENTRY_BYTES);
    assert!(!tables.reserve_empty(2, 1).unwrap());
    assert!(tables.pointers[2].is_null() && tables.owned[2].is_empty());
    assert_eq!(tables.pointers[0], address);
    assert!(tables.vacant_entry(2, 0).is_err());
}
