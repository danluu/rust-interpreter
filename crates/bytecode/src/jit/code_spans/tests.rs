use super::*;
use crate::{Slot, VERSION};

fn fixture() -> Program {
    let functions = (0..3).map(|id| Function {
        name: format!("function_{id}"), frame_size: 32, frame_align: 16, registers: 6,
        args: vec![], result: Slot { offset: 0, size: 0 }, code: vec![
            Op::Local { dst: 0, offset: 0 }, Op::Imm { dst: 1, value: 1 },
            Op::Assert { value: 1, expected: true, message: format!("assertion_{id}") },
            Op::Store { address: 0, src: 1, size: 8 },
            Op::Binary { dst: 2, overflow: 3, kind: Binary::Div, left: 1, right: 1, bits: 64, signed: true },
            Op::Switch { value: 2, cases: vec![(1, 6)], otherwise: 0 },
            Op::Imm { dst: 4, value: 0 }, Op::Copy { dst: 0, src: 0, size: 8 },
            Op::Call { function: 2, args: vec![], destination: 0 }, Op::Return,
        ],
    }).collect();
    Program { version: VERSION, target: "aarch64-apple-darwin".into(), entry: 0,
        data: vec![0; 16], statics: vec![], thread_locals: vec![], functions }
}

fn jit(p: &Program, profiled: bool, resumable: bool, persistent: bool, capacity: usize) -> Jit<'_> {
    if resumable { Jit::new_resumable(p, profiled, capacity, persistent).unwrap() }
    else { Jit::new_with_options(p, profiled, capacity, false, persistent).unwrap() }
}

#[test]
fn reconstruction_preserves_publication_order_assertions_entries_and_all_modes() {
    let p = fixture(); crate::validate(&p).unwrap();
    for profiled in [false, true] { for resumable in [false, true] { for persistent in [false, true] {
        for order in [[2, 0, 1], [1, 2, 0]] {
            let mut jit = jit(&p, profiled, resumable, persistent, MAX_CODE_BYTES);
            for id in order { jit.ensure_function(id).unwrap(); }
            let before = (jit.bytes, jit.operations, jit.compile_nanos, jit.assertions.len(),
                jit.compiled_functions, jit.declined_functions, jit.register_pairs);
            let bytes = jit.code.as_ref().unwrap().published().1.to_vec();
            let map = jit.operation_map().unwrap();
            assert_eq!(map.functions.iter().map(|f| f.function).collect::<Vec<_>>(), order);
            assert_eq!(map.code_bytes, bytes.len());
            assert_eq!(map.functions.iter().map(|f| f.assertion_base).collect::<Vec<_>>(), [0, 1, 2]);
            assert!(map.functions.iter().all(|f| f.assertion_count == 1));
            let rows: Vec<_> = map.functions.iter().flat_map(|f| &f.spans).collect();
            assert!(rows.iter().any(|s| s.kind == Kind::Operation && s.offset == s.end));
            assert!(rows.iter().any(|s| s.kind == Kind::AssertionTail));
            assert!(rows.iter().any(|s| s.kind == Kind::FaultTail));
            assert!(rows.iter().any(|s| s.kind == Kind::BudgetFallback));
            assert!(rows.iter().any(|s| s.pc == Some(5) && s.kind == Kind::Operation));
            assert_eq!(rows.iter().any(|s| s.kind == Kind::Profile), profiled);
            assert_eq!(rows.iter().any(|s| s.kind == Kind::Transition), resumable);
            let mut cursor = 0;
            for row in rows { assert_eq!(row.offset, cursor); cursor = row.end; }
            assert_eq!(cursor, bytes.len());
            assert_eq!((jit.bytes, jit.operations, jit.compile_nanos, jit.assertions.len(),
                jit.compiled_functions, jit.declined_functions, jit.register_pairs), before);
            assert_eq!(jit.code.as_ref().unwrap().published().1, bytes);
        }
    } } }
}

#[test]
fn reconstruction_reuses_original_table_admission_instead_of_counting_it_twice() {
    let p = fixture();
    let mut jit = jit(&p, false, true, true, MAX_CODE_BYTES);
    for id in [1, 0] { jit.ensure_function(id).unwrap(); }
    let tables = jit.resumable.as_mut().unwrap();
    let used = tables.published(0).len() + tables.published(1).len();
    // Fill the remaining entry budget using an otherwise unprepared function.
    // This is a table-admission fixture, not a claim of executed guest work.
    tables.publish(2, vec![0; 16 * 1024 * 1024 / 8 - used]);
    assert!(!tables.fits(p.functions[0].code.len()));
    assert!(jit.emit_function(&p.functions[0], MAX_CODE_BYTES / 4).unwrap().is_none());
    let map = jit.operation_map().unwrap();
    assert_eq!(map.functions.iter().map(|f| f.function).collect::<Vec<_>>(), [1, 0]);
}

#[test]
fn declined_functions_consume_no_mapping_bytes_or_assertion_identities() {
    let mut p = fixture();
    p.functions[1].code.splice(2..2, (0..3000).map(|_| Op::Store { address: 0, src: 1, size: 8 }));
    // Remove branches whose old targets no longer describe this large body.
    p.functions[1].code.retain(|op| !matches!(op, Op::Switch { .. }));
    crate::validate(&p).unwrap();
    for resumable in [false, true] {
        let cold = jit(&p, true, resumable, true, MAX_CODE_BYTES);
        let capacity = [0, 2].into_iter().map(|id| cold.emit_function(&p.functions[id],
            MAX_CODE_BYTES / 4).unwrap().unwrap().words.len() * 4).sum();
        let mut limited = jit(&p, true, resumable, true, capacity);
        for id in [0, 1, 2] { limited.ensure_function(id).unwrap(); }
        assert_eq!(limited.declined_functions, 1);
        let map = limited.operation_map().unwrap();
        assert_eq!(map.functions.iter().map(|f| (f.function, f.assertion_base)).collect::<Vec<_>>(), [(0, 0), (2, 1)]);
        let mut empty = jit(&p, true, resumable, true, 0);
        for id in 0..3 { empty.ensure_function(id).unwrap(); }
        let map = empty.operation_map().unwrap();
        assert_eq!((map.functions.len(), map.spans, map.code_bytes), (0, 0, 0));
    }
}

#[test]
fn incomplete_overlapping_or_misattributed_spans_and_corrupt_words_are_rejected() {
    let p = fixture();
    let jit = jit(&p, true, true, true, MAX_CODE_BYTES);
    for corruption in 0..5 {
        let mut collector = Collector { rows: vec![], limit: MAX_SPANS };
        let staged = jit.emit_function_inner(&p.functions[0], MAX_CODE_BYTES / 4, 0,
            Some(&mut collector)).unwrap().unwrap();
        collector.validate(&p.functions[0], &staged).unwrap();
        match corruption {
            0 => { collector.rows.remove(0); },
            1 => collector.rows[0].end += 4,
            2 => collector.rows[0].region_pc = usize::MAX,
            3 => collector.rows.iter_mut().find(|s| s.pc.is_some()).unwrap().pc = Some(usize::MAX),
            4 => { collector.rows.retain(|s| s.pc != Some(5)); },
            _ => unreachable!(),
        }
        assert!(collector.validate(&p.functions[0], &staged).is_err());
        let mut bytes: Vec<u8> = staged.words.iter().flat_map(|w| w.to_le_bytes()).collect();
        verify_words(&staged.words, &bytes).unwrap();
        bytes[0] ^= 1;
        assert!(verify_words(&staged.words, &bytes).is_err());
        assert!(verify_words(&staged.words, &bytes[1..]).is_err());
    }
    let mut published = Jit::new_resumable(&p, true, MAX_CODE_BYTES, true).unwrap();
    published.ensure_function(0).unwrap();
    published.assertions[0].kind = FaultKind::Trap;
    assert!(published.operation_map().unwrap_err().contains("assertion mismatch"));
    published.assertions[0].kind = FaultKind::Assertion;
    published.blocks[0][0].as_mut().unwrap().end -= 1;
    assert!(published.operation_map().unwrap_err().contains("entry mismatch"));
}

#[test]
fn collectors_and_output_are_bounded_and_default_emission_keeps_no_records() {
    let mut collector = Collector { rows: vec![], limit: 1 };
    record(&mut None, usize::MAX, usize::MAX, Some(0), Kind::Operation, 1, 2).unwrap();
    record(&mut Some(&mut collector), 0, 0, Some(0), Kind::Operation, 0, 0).unwrap();
    assert_eq!(collector.rows.len(), 1);
    assert!(matches!(record(&mut Some(&mut collector), 0, 0, Some(1), Kind::Operation, 0, 1),
        Err(EmitError::Limit(CodegenLimit::OperationMap))));
    let mut collector = Collector { rows: vec![], limit: 2 };
    assert!(matches!(record(&mut Some(&mut collector), usize::MAX, 0, Some(0), Kind::Operation, 1, 2),
        Err(EmitError::InvalidRelocation(_))));
    let mut bounded = Limited { writer: Vec::new(), remaining: 3 };
    bounded.write_all(b"abc").unwrap();
    assert!(bounded.write_all(b"d").is_err());
    assert_eq!(bounded.writer, b"abc");
}
