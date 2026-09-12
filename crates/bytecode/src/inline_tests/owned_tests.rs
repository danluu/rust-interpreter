use super::*;

fn identity_program() -> Program {
    root(leaf("identity", 16, 2, vec![Slot { offset: 0, size: 8 }],
        Slot { offset: 0, size: 8 }, vec![
            Op::Local { dst: 0, offset: 0 },
            Op::Load { dst: 1, address: 0, size: 8 },
            Op::Return,
        ]), &[8], 32)
}

#[test]
fn owned_storage_survives_both_no_selection_and_successful_expansion() {
    for caller_growth in [0, 4096] {
        let mut p = identity_program();
        p.data.extend(0u8..=255);
        p.statics = vec![17; 32];
        p.thread_locals = vec![Slot { offset: 16, size: 16 }];
        let options = inline::Options { caller_growth, ..options() };
        let (expected, expected_report) = inline::transform(&p, options).unwrap();
        let storage = (p.functions.as_ptr(), p.data.as_ptr(), p.statics.as_ptr(),
            p.thread_locals.as_ptr(), p.target.as_ptr());
        let unchanged = (&p.functions[1].name, &p.functions[1].args, &p.functions[1].code);
        let unchanged = (unchanged.0.as_ptr(), unchanged.1.as_ptr(), unchanged.2.as_ptr());
        let caller_code = p.functions[0].code.as_ptr();
        let (q, report) = inline::transform_owned(p, options).unwrap();
        assert_eq!(bincode::serialize(&q).unwrap(), bincode::serialize(&expected).unwrap());
        assert_eq!(report, expected_report);
        assert_eq!(report["selected_sites"], usize::from(caller_growth != 0));
        assert_eq!(storage, (q.functions.as_ptr(), q.data.as_ptr(), q.statics.as_ptr(),
            q.thread_locals.as_ptr(), q.target.as_ptr()));
        assert_eq!(unchanged, (q.functions[1].name.as_ptr(), q.functions[1].args.as_ptr(),
            q.functions[1].code.as_ptr()));
        if caller_growth == 0 {
            assert_eq!(caller_code, q.functions[0].code.as_ptr());
        }
    }
}

#[test]
fn validation_still_precedes_option_errors() {
    let mut p = identity_program();
    let invalid_options = inline::Options { caller_growth: 4097, ..options() };
    assert_eq!(checked_transform(&p, invalid_options).unwrap_err(),
        "leaf inlining options exceed bounded limits");
    p.functions[0].code[0] = Op::Jump { target: usize::MAX };
    let validation_error = crate::validate(&p).unwrap_err();
    assert!(validation_error.contains("invalid branch"));
    assert_eq!(checked_transform(&p, invalid_options).unwrap_err(), validation_error);
}

#[test]
fn later_callers_keep_edges_to_original_nonleaf_functions() {
    let mut p = identity_program();
    let mut later = p.functions[0].clone();
    later.name = "later caller".into();
    // Function 0 expands first. Function 2 still calls that original nonleaf,
    // then independently expands its own direct edge to leaf 1.
    later.code.insert(2, Op::Call { function: 0, args: vec![0], destination: 1 });
    p.functions.push(later);
    p.entry = 2;
    let original_leaf = bincode::serialize(&p.functions[1]).unwrap();
    let (q, report) = checked_transform(&p, options()).unwrap();
    assert_eq!(report["selected_sites"], 2);
    assert_eq!(report["added_operations_upper_bound"], 24);
    let changed: Vec<_> = report["changed_callers"].as_array().unwrap().iter()
        .map(|caller| caller["function"].as_u64().unwrap()).collect();
    assert_eq!(changed, [0, 2]);
    assert_eq!(bincode::serialize(&q.functions[1]).unwrap(), original_leaf);
    let direct: Vec<_> = q.functions[2].code.iter().filter_map(|op| match op {
        Op::Call { function, .. } => Some(*function), _ => None,
    }).collect();
    assert_eq!(direct, [0]);
    for value in [0, 7, u64::MAX as u128] {
        assert_eq!(execute_with_engine(&p, &[value], Limits::default(), Engine::Interpreter).unwrap().value, value);
        assert_eq!(execute_with_engine(&q, &[value], Limits::default(), Engine::Interpreter).unwrap().value, value);
    }
}

#[test]
fn rejected_caller_restores_budget_before_later_admission() {
    let branch = leaf("branch", 16, 1, vec![], Slot { offset: 0, size: 0 }, vec![
        Op::Imm { dst: 0, value: 1 },
        Op::Assert { value: 0, expected: true, message: "check".into() },
        Op::Switch { value: 0, cases: vec![(1, 3)], otherwise: 4 },
        Op::Return,
        Op::Return,
    ]);
    let mut p = root(branch, &[], 0);
    let mut later = p.functions[0].clone();
    later.name = "later admitted".into();
    p.functions.push(later);
    p.functions[0].code.insert(0, Op::Imm { dst: 3, value: 43 });
    p.functions[0].code.insert(3, Op::Store { address: 0, src: 3, size: 8 });
    let rejected = bincode::serialize(&p.functions[0]).unwrap();
    // Original size is 29 operations; the 14-operation growth allowance can
    // admit either 11-operation expansion, but not both without rollback.
    // Diagnostic accounting must also undo the rejected copy of "check".
    let (q, report) = checked_transform(&p,
        inline::Options { program_growth_percent: 50, ..options() }).unwrap();
    assert_eq!(bincode::serialize(&q.functions[0]).unwrap(), rejected);
    assert_eq!(report, serde_json::json!({
        "selected_sites": 1, "original_operations": 29, "new_operations": 38,
        "added_operations_upper_bound": 11, "max_leaf_operations": 192,
        "max_program_growth_percent": 50, "cloned_diagnostic_bytes": 27,
        "changed_callers": [{"function": 2, "name": "later admitted", "sites": 1,
            "old_operations": 11, "new_operations": 20, "removed_jumps": 2,
            "old_frame_size": 64, "new_frame_size": 80,
            "old_registers": 4, "new_registers": 8,
            "needed_register_zeroes_before": false, "needed_register_zeroes_after": false}],
    }));
}

#[test]
fn owned_pipeline_matches_borrowed_pass_order_and_retains_data() {
    let mut p = identity_program();
    p.functions.push(leaf("forwarder", 16, 2,
        vec![Slot { offset: 0, size: 8 }], Slot { offset: 8, size: 8 }, vec![
            Op::Local { dst: 0, offset: 0 },
            Op::Local { dst: 1, offset: 8 },
            Op::Call { function: 1, args: vec![0], destination: 1 },
            Op::Return,
        ]));
    if let Op::Call { function, .. } = &mut p.functions[0].code[2] {
        *function = 2;
    } else {
        panic!("expected fixture call");
    }
    let mut reference = p.clone();
    let first = crate::eliminate_direct_forwarders(&mut reference).unwrap();
    assert_eq!(first.retargeted_calls, 1);
    let (mut reference, details) = inline::transform(&reference, options()).unwrap();
    let last = crate::eliminate_direct_forwarders(&mut reference).unwrap();
    let data = p.data.as_ptr();
    let (q, report) = crate::optimize_calls(p, Some(options())).unwrap();
    assert_eq!(bincode::serialize(&q).unwrap(), bincode::serialize(&reference).unwrap());
    assert_eq!(report.forwarding_before_inline, Some(first));
    assert_eq!(report.inlining, Some(details));
    assert_eq!(report.final_forwarding, last);
    assert_eq!(q.data.as_ptr(), data);
}
