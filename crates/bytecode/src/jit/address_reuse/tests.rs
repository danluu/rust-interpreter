use super::*;
use crate::{Slot, VERSION};

fn function(code: Vec<Op>) -> Function {
    Function { name: "address-counts".into(), frame_size: 32, frame_align: 16,
        registers: 64, args: vec![], result: Slot { offset: 0, size: 0 }, code }
}

fn count(f: &Function, intervals: &[(usize, usize, u64)]) -> (Counts, Vec<Site>) {
    let mut counts = Counts::default();
    let mut sites = vec![];
    for &(start, end, hits) in intervals { interval(f, start, end, hits, &mut counts, &mut sites).unwrap(); }
    (counts, sites)
}

#[test]
fn sizes_and_write_permission_have_independent_containment() {
    let f = function(vec![Op::Imm { dst: 0, value: 1 },
        Op::Load { dst: 1, address: 0, size: 8 },
        Op::Store { address: 0, src: 1, size: 8 },
        Op::Load { dst: 2, address: 0, size: 4 },
        Op::Store { address: 0, src: 2, size: 4 },
        Op::Load { dst: 3, address: 0, size: 16 },
        Op::Store { address: 0, src: 3, size: 16 }]);
    let (c, sites) = count(&f, &[(0, f.code.len(), 3)]);
    assert_eq!((c.accesses, c.baseline_checks, c.reusable_checks, c.permission_upgrades), (18, 18, 6, 6));
    assert_eq!(sites.iter().map(|s| (s.pc, s.prior_pc)).collect::<Vec<_>>(), [(3, 1), (4, 2)]);
}

#[test]
fn definitions_zero_sizes_intervals_and_opaque_effects_do_not_preserve_proofs() {
    let f = function(vec![Op::Imm { dst: 0, value: 1 },
        Op::Load { dst: 1, address: 0, size: 0 },
        Op::Load { dst: 0, address: 0, size: 8 },
        Op::Load { dst: 1, address: 0, size: 8 },
        Op::ResetThreadLocals,
        Op::Load { dst: 1, address: 0, size: 8 },
        Op::Imm { dst: 0, value: 1 },
        Op::Load { dst: 1, address: 0, size: 8 }]);
    let (c, _) = count(&f, &[(0, f.code.len(), 1)]);
    assert_eq!((c.accesses, c.reusable_checks, c.definition_invalidations), (4, 0, 2));
    let f = function(vec![Op::Load { dst: 1, address: 0, size: 8 },
        Op::Load { dst: 2, address: 0, size: 8 }]);
    assert_eq!(count(&f, &[(0, 1, 5), (1, 2, 7)]).0.reusable_checks, 0);
    // Independent overlapping entries each start with no proof.
    assert_eq!(count(&f, &[(0, 2, 5), (1, 2, 7)]).0.reusable_checks, 5);
}

#[test]
fn existing_local_folding_is_excluded_and_aliased_outputs_keep_the_last_definition() {
    let mut f = function(vec![Op::Local { dst: 0, offset: 0 }, Op::Imm { dst: 1, value: 8 },
        Op::Binary { dst: 2, overflow: 3, op: Binary::Add, a: 0, b: 1, bits: 64, signed: false },
        Op::Load { dst: 4, address: 2, size: 8 }, Op::Store { address: 2, src: 4, size: 8 },
        Op::Imm { dst: 2, value: 1 }, Op::Load { dst: 5, address: 2, size: 8 },
        Op::Load { dst: 6, address: 2, size: 8 }]);
    let (c, _) = count(&f, &[(0, f.code.len(), 1)]);
    assert_eq!((c.known_local, c.baseline_checks, c.reusable_checks), (2, 2, 1));
    if let Op::Binary { overflow, .. } = &mut f.code[2] { *overflow = 2; }
    let (c, _) = count(&f, &[(0, 5, 1)]);
    assert_eq!((c.known_local, c.baseline_checks), (0, 2));
}

#[test]
fn cache_capacity_and_work_bounds_decline_conservatively() {
    let mut code: Vec<_> = (0..17).map(|address| Op::Load { dst: 63, address, size: 8 }).collect();
    code.push(Op::Load { dst: 63, address: 0, size: 8 });
    code.push(Op::Load { dst: 63, address: 0, size: 4 });
    let f = function(code);
    let (c, _) = count(&f, &[(0, f.code.len(), 2)]);
    assert_eq!((c.capacity_clears, c.reusable_checks), (2, 2));
    let cost = f.code.len() * 7;
    assert_eq!(interval_cost(&f, &[(0, f.code.len(), 1)], cost), Some(cost));
    assert_eq!(interval_cost(&f, &[(0, f.code.len(), 1)], cost - 1), None);
    assert_eq!(interval_cost(&f, &[(0, f.code.len(), 1); 2], cost), None);
    let mut f = f; f.registers = MAX_FUNCTION + 1;
    assert_eq!(interval_cost(&f, &[(0, 1, 1)], usize::MAX), None);
}

#[test]
fn public_census_checks_profile_shape_and_rejects_counter_overflow() {
    let f = function(vec![Op::Imm { dst: 0, value: 1 },
        Op::Load { dst: 1, address: 0, size: 8 },
        Op::Load { dst: 2, address: 0, size: 4 }, Op::Return]);
    let mut profile = serde_json::json!({"functions": [{"name": f.name,
        "frame_size": f.frame_size, "registers": f.registers,
        "operations": f.code.iter().map(|op| format!("{op:?}")).collect::<Vec<_>>(),
        "interpreted": [0,0,0,0], "jit_blocks": [5,0,0,5], "jit_block_ends": [3,0,0,4],
        "jit_tree_blocks": [0,0,0,0], "jit_tree_block_ends": [0,0,0,0]}]});
    let p = Program { version: VERSION, target: "aarch64-apple-darwin".into(), entry: 0,
        data: vec![0], statics: vec![], thread_locals: vec![], functions: vec![f] };
    let bytes = serde_json::to_vec(&profile).unwrap();
    let report = census(&p, &bytes).unwrap();
    assert_eq!(report["counts"]["reusable_checks"], 5);
    assert_eq!(report["guest_instructions_executed"], 0);
    profile["functions"][0]["operations"][1] = "different".into();
    assert!(census(&p, &serde_json::to_vec(&profile).unwrap()).is_err());
    let mut profile: serde_json::Value = serde_json::from_slice(&bytes).unwrap();
    profile["functions"][0]["jit_blocks"][0] = u64::MAX.into();
    assert!(census(&p, &serde_json::to_vec(&profile).unwrap()).is_err());
}
