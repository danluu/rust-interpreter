use super::*;
use crate::Slot;

fn f(code: Vec<Op>) -> Function {
    Function { name:"facts".into(), frame_size:32, frame_align:16, registers:8,
        args:vec![],result:Slot {offset:0,size:0},code }
}
fn run(f: &Function, intervals: &[(usize,usize,u64)]) -> serde_json::Value {
    function(f,intervals,&mut Budget {used:0,limit:MAX_FUNCTION_WORK}).unwrap()
}
fn load(address: Reg) -> Op { Op::Load {dst:7,address,size:8} }
fn jump(target: usize) -> Op { Op::Jump {target} }
fn branch(left: usize, right: usize) -> Op {
    Op::Switch {value:6,cases:vec![(0,left)],otherwise:right}
}

#[test]
fn stable_cross_region_locals_include_both_copy_addresses() {
    let f=f(vec![Op::Local {dst:0,offset:0},Op::Local {dst:1,offset:8},jump(3),
        Op::Copy {dst:1,src:0,size:8},load(0),Op::Return]);
    let r=run(&f,&[(0,3,2),(3,6,2)]);
    assert_eq!(r["weighted_accesses"],6); assert_eq!(r["region_unknown_accesses"],6);
    assert_eq!(r["additional_local_accesses"],6);assert_eq!(r["additional_writes"],2);
    assert_eq!(r["additional_copy_addresses"],4);
    let r=run(&f,&[(0,6,2)]);assert_eq!(r["existing_local_accesses"],6);
    assert_eq!(r["additional_local_accesses"],0);
}

#[test]
fn identical_joins_are_known_but_conflicts_and_skipped_definitions_are_not() {
    for (right,expected) in [(Op::Local {dst:0,offset:8},5),
        (Op::Local {dst:0,offset:16},0),(Op::Imm {dst:0,value:0},0),(jump(4),0)] {
        let f=f(vec![branch(1,3),Op::Local {dst:0,offset:8},jump(4),right,load(0),Op::Return]);
        assert_eq!(run(&f,&[(4,6,5)])["additional_local_accesses"],expected);
    }
}

#[test]
fn loops_reach_a_fixed_point_without_inventing_initial_values() {
    let stable=f(vec![Op::Local {dst:0,offset:8},jump(2),load(0),branch(2,4),Op::Return]);
    assert_eq!(run(&stable,&[(2,4,10)])["additional_local_accesses"],10);
    let conflicting=f(vec![Op::Local {dst:0,offset:8},jump(2),load(0),
        Op::Local {dst:0,offset:16},branch(2,5),Op::Return]);
    assert_eq!(run(&conflicting,&[(2,5,10)])["additional_local_accesses"],0);
    let skipped=f(vec![jump(2),Op::Local {dst:0,offset:8},load(0),branch(1,4),Op::Return]);
    assert_eq!(run(&skipped,&[(2,4,10)])["additional_local_accesses"],0);
}

#[test]
fn reads_precede_aliased_outputs_and_overflow_output_is_last() {
    let binary=|dst,overflow| Op::Binary {dst,overflow,op:Binary::Add,a:0,b:1,bits:64,signed:false};
    let mut f=f(vec![Op::Local {dst:0,offset:8},Op::Imm {dst:1,value:8},binary(0,2),jump(4),load(0),Op::Return]);
    assert_eq!(run(&f,&[(4,6,3)])["additional_local_accesses"],3);
    f.code[2]=binary(0,0);
    assert_eq!(run(&f,&[(4,6,3)])["additional_local_accesses"],0);
    f.code[0]=Op::Imm {dst:3,value:8}; // Read of register0 before its first write.
    f.code[2]=binary(0,2);
    assert_eq!(run(&f,&[(4,6,3)])["additional_local_accesses"],0);
}

#[test]
fn calls_do_not_redefine_caller_registers_but_loads_do() {
    let mut f=f(vec![Op::Local {dst:0,offset:8},
        Op::Call {function:0,args:vec![0],destination:0},jump(3),load(0),Op::Return]);
    assert_eq!(run(&f,&[(3,5,3)])["additional_local_accesses"],3);
    f.code[1]=Op::Load {dst:0,address:0,size:8};
    assert_eq!(run(&f,&[(3,5,3)])["additional_local_accesses"],0);
}

#[test]
fn complete_extents_and_local_addition_never_accept_overflow() {
    for (offset,size,expected) in [(24,8,2),(25,8,0),(32,0,0),(usize::MAX,8,0)] {
        let f=f(vec![Op::Local {dst:0,offset},jump(2),Op::Copy {dst:0,src:0,size},Op::Return]);
        assert_eq!(run(&f,&[(2,4,1)])["additional_local_accesses"],expected);
    }
    let f=f(vec![Op::Local {dst:0,offset:8},Op::Imm {dst:1,value:u64::MAX.into()},
        Op::Binary {dst:0,overflow:2,op:Binary::Add,a:0,b:1,bits:64,signed:false},
        jump(4),load(0),Op::Return]);
    assert_eq!(run(&f,&[(4,6,1)])["additional_local_accesses"],0);
}

#[test]
fn unknown_outputs_and_all_branch_successors_remain_conservative() {
    let mut f=f(vec![Op::Imm {dst:6,value:0},branch(2,4),
        Op::Local {dst:0,offset:8},jump(5),Op::Local {dst:0,offset:16},load(0),Op::Return]);
    // No constant-branch pruning: both semantic successors participate.
    assert_eq!(run(&f,&[(5,7,4)])["additional_local_accesses"],0);
    f.code[4]=Op::Local {dst:0,offset:8};
    assert_eq!(run(&f,&[(5,7,4)])["additional_local_accesses"],4);
    f.code[4]=Op::Cast {dst:0,src:0,from:64,to:64,signed:false};
    assert_eq!(run(&f,&[(5,7,4)])["additional_local_accesses"],0);
}

#[test]
fn work_and_counter_bounds_decline_without_partial_opportunity_claims() {
    let f=f(vec![Op::Local {dst:0,offset:8},jump(2),Op::Copy {dst:0,src:0,size:8},Op::Return]);
    assert!(function(&f,&[(2,4,1)],&mut Budget {used:0,limit:1}).is_none());
    assert!(function(&f,&[(2,4,u64::MAX)],&mut Budget {used:0,limit:MAX_FUNCTION_WORK}).is_none());
    let oversized=Function {registers:MAX_ITEMS+1,..f};
    assert!(analyze(&oversized,&mut Budget {used:0,limit:MAX_FUNCTION_WORK}).is_none());
}
