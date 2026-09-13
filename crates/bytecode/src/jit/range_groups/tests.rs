use super::*;
use crate::Slot;

fn load(dst:Reg,address:Reg)->Op {Op::Load {dst,address,size:8}}
fn add(dst:Reg,overflow:Reg,a:Reg,b:Reg)->Op {Op::Binary {dst,overflow,op:Binary::Add,a,b,bits:64,signed:false}}
fn function_input(code:Vec<Op>)->Function {
    Function {name:"groups".into(),frame_size:64,frame_align:16,registers:8,args:vec![],result:Slot {offset:0,size:0},code}
}
fn run(code:Vec<Op>)->serde_json::Value {
    let f=function_input(code);function(&f,&[(0,f.code.len(),5)],&mut MAX_FUNCTION_WORK.clone()).unwrap()
}
fn apply(state:&mut State,code:&[Op]) {for op in code {state.transfer(op,64);}}

#[test]
fn entry_register_offsets_form_one_complete_read_write_group() {
    let r=run(vec![load(7,0),Op::Imm {dst:1,value:8},add(2,6,0,1),load(7,2),
        Op::Imm {dst:1,value:16},add(3,6,0,1),Op::Store {address:3,src:7,size:8}]);
    assert_eq!(r["counts"]["best_group_addresses"],15);
    assert_eq!(r["counts"]["best_group_redundant_checks"],10);
    let g=&r["top_groups"][0];assert_eq!(g["span"],24);assert_eq!(g["writes"],1);
    assert_eq!(g["root"],serde_json::json!({"Register":0}));
}

#[test]
fn entry_slot_identity_survives_full_width_local_storage() {
    let mut state=State::default();
    apply(&mut state,&[Op::Local {dst:0,offset:0},load(1,0),Op::Local {dst:2,offset:16},
        Op::Store {address:2,src:1,size:8},load(3,2)]);
    assert_eq!(state.get(1),Value::Pointer(Root::FrameSlot(0),0));
    assert_eq!(state.get(3),state.get(1));
    apply(&mut state,&[Op::Cast {dst:4,src:3,from:64,to:64,signed:true}]);
    assert_eq!(state.get(4),state.get(1));
}

#[test]
fn overlapping_and_unknown_writes_do_not_invent_entry_slot_values() {
    let mut state=State::default();
    apply(&mut state,&[Op::Local {dst:0,offset:0},load(1,0),Op::Local {dst:2,offset:4},
        Op::Imm {dst:5,value:0},Op::Store {address:2,src:5,size:4},load(3,0)]);
    assert_eq!(state.get(3),Value::Opaque);
    assert_eq!(state.get(1),Value::Pointer(Root::FrameSlot(0),0));
    apply(&mut state,&[Op::Store {address:6,src:5,size:8},Op::Local {dst:2,offset:32},load(4,2)]);
    assert_eq!(state.get(4),Value::Opaque);
    assert_eq!(state.get(1),Value::Pointer(Root::FrameSlot(0),0));
}

#[test]
fn overlapping_copy_captures_source_before_invalidating_destination() {
    let mut state=State::default();
    apply(&mut state,&[Op::Local {dst:0,offset:0},Op::Local {dst:2,offset:4},
        Op::Copy {dst:2,src:0,size:8},load(3,2),load(4,0)]);
    assert_eq!(state.get(3),Value::Pointer(Root::FrameSlot(0),0));
    assert_eq!(state.get(4),Value::Opaque);
    apply(&mut state,&[Op::Call {function:0,args:vec![0],destination:2},load(4,2)]);
    assert_eq!(state.get(4),Value::Opaque);
    assert_eq!(state.get(3),Value::Pointer(Root::FrameSlot(0),0));
}

#[test]
fn aliased_outputs_and_opaque_loads_do_not_reuse_old_register_identity() {
    let mut state=State::default();
    apply(&mut state,&[Op::Imm {dst:1,value:8},add(0,6,0,1)]);
    assert_eq!(state.get(0),Value::Pointer(Root::Register(0),8));
    state.transfer(&add(0,0,0,1),64);assert_eq!(state.get(0),Value::Opaque);
    let r=run(vec![load(0,1),load(7,0),load(7,0),load(7,0)]);
    assert_eq!(r["counts"]["entry_pointer_addresses"],5);
    assert_eq!(r["counts"]["best_group_addresses"],0);
}

#[test]
fn signed_offsets_are_bounded_without_assuming_nonwrapping_guest_arithmetic() {
    let r=run(vec![load(7,0),Op::Imm {dst:1,value:(u64::MAX-7).into()},add(2,6,0,1),load(7,2),load(7,2)]);
    assert_eq!(r["top_groups"][0]["minimum_offset"],-8);
    assert_eq!(r["top_groups"][0]["span"],16);
    let r=run(vec![load(7,0),Op::Imm {dst:1,value:4097},add(2,6,0,1),load(7,2),load(7,2)]);
    assert_eq!(r["counts"]["best_group_addresses"],0);
}

#[test]
fn best_group_and_all_groups_are_distinct_and_never_cross_region_boundaries() {
    let code=vec![load(7,0),load(7,0),load(7,0),load(7,1),load(7,1),load(7,1),load(7,1)];
    let r=run(code.clone());assert_eq!(r["counts"]["all_group_addresses"],35);
    assert_eq!(r["counts"]["best_group_addresses"],20);
    let f=function_input(code);
    let r=function(&f,&[(0,2,5),(2,4,5),(4,6,5),(6,7,5)],&mut MAX_FUNCTION_WORK.clone()).unwrap();
    assert_eq!(r["counts"]["best_group_addresses"],0);
}

#[test]
fn copy_endpoints_and_zero_size_preserve_counting_scope() {
    let r=run(vec![Op::Copy {dst:0,src:0,size:8},load(7,0),Op::Copy {dst:0,src:0,size:0}]);
    assert_eq!(r["counts"]["fixed_addresses"],15);
    assert_eq!(r["counts"]["best_group_addresses"],15);
    assert_eq!(r["top_groups"][0]["writes"],1);
}

#[test]
fn site_report_truncation_keeps_counts_and_exhaustion_drops_partial_results() {
    let f=function_input(vec![load(7,0);70]);
    let r=function(&f,&[(0,70,1)],&mut MAX_FUNCTION_WORK.clone()).unwrap();
    assert_eq!(r["top_groups"][0]["accesses"],70);
    assert_eq!(r["top_groups"][0]["sites"].as_array().unwrap().len(),64);
    assert_eq!(r["top_groups"][0]["sites_truncated"],true);
    assert!(function(&f,&[(0,70,1)],&mut 1).is_none());
    assert!(function(&f,&[(0,70,u64::MAX)],&mut MAX_FUNCTION_WORK.clone()).is_none());
}
