use super::*;
use rust_interp_bytecode::{Slot, VERSION};

fn function(code: Vec<Op>) -> Function {
    Function { name: "caller".into(), frame_size: 64, frame_align: 8, registers: 4,
        args: vec![], result: Slot { offset: 0, size: 0 }, code }
}
fn counts(f: &Function) -> Counts {
    let n = f.code.len();
    Counts { name: f.name.clone(), frame_size: f.frame_size, registers: f.registers,
        operations: f.code.iter().map(|op| format!("{op:?}")).collect(),
        interpreted: vec![0;n], jit_blocks: vec![0;n], jit_block_ends: vec![0;n],
        jit_tree_blocks: vec![0;n], jit_tree_block_ends: vec![0;n] }
}
fn at_calls(f: &Function) -> Vec<bool> {
    let starts = block_starts(f); let mut facts = vec![None;f.registers]; let mut found = vec![];
    for (pc, op) in f.code.iter().enumerate() {
        if starts[pc] { facts.fill(None); }
        if let Op::Call { destination, .. } = op { found.push(in_frame(&facts,*destination,8,f.frame_size)); }
        transfer(op,&mut facts,f.frame_size);
    }
    found
}
fn call() -> Op { Op::Call { function:0, args:vec![], destination:0 } }

#[test]
fn calls_and_memory_writes_preserve_caller_register_addresses() {
    assert_eq!(at_calls(&function(vec![Op::Local {dst:0,offset:8},call(),
        Op::Store {address:0,src:1,size:8},call(),Op::Return])),[true,true]);
}
#[test]
fn skipped_definitions_branch_merges_and_backedges_reset_facts() {
    assert_eq!(at_calls(&function(vec![Op::Jump{target:2},Op::Local{dst:0,offset:8},call(),Op::Return])),[false]);
    assert_eq!(at_calls(&function(vec![Op::Local{dst:0,offset:8},
        Op::Switch{value:1,cases:vec![(0,3)],otherwise:2},Op::Local{dst:0,offset:8},call(),Op::Return])),[false]);
    assert_eq!(at_calls(&function(vec![Op::Local{dst:0,offset:8},call(),Op::Load{dst:0,address:1,size:8},
        Op::Jump{target:1}])),[false]);
}
#[test]
fn aliased_load_kills_address_fact_and_reset_does_not_restore_it() {
    assert_eq!(at_calls(&function(vec![Op::Local{dst:0,offset:8},Op::Load{dst:0,address:0,size:8},call(),Op::Return])),[false]);
}
#[test]
fn target_width_addition_and_output_alias_order_are_preserved() {
    let mut facts=vec![Some(Fact::Local(8)),Some(Fact::Imm((1u128<<100)+16)),None,None];
    transfer(&Op::Binary{dst:0,overflow:2,op:Binary::Add,a:0,b:1,bits:64,signed:false},&mut facts,64);
    assert_eq!(facts[0],Some(Fact::Local(24))); assert_eq!(facts[2],Some(Fact::Imm(0)));
    transfer(&Op::Binary{dst:0,overflow:0,op:Binary::Add,a:0,b:1,bits:64,signed:false},&mut facts,64);
    assert_eq!(facts[0],Some(Fact::Imm(0)));
    facts[0]=Some(Fact::Local(8));
    transfer(&Op::Binary{dst:0,overflow:2,op:Binary::Add,a:0,b:1,bits:32,signed:false},&mut facts,64);
    assert_eq!(facts[0],None); assert_eq!(facts[2],None);
}
#[test]
fn bounds_and_zero_size_slots_remain_distinct_from_checks() {
    let f=function(vec![Op::Return]);let facts=vec![Some(Fact::Local(60)),None,None,None];
    assert!(in_frame(&facts,0,4,64));assert!(!in_frame(&facts,0,5,64));
    assert!(!in_frame(&[Some(Fact::Local(usize::MAX))],0,2,64));
    let mut t=Totals::default();
    observe(&f,&facts,&[4,8,0],&[0,0,1],0,4,7,2,Some(64),false,&mut t);
    assert_eq!((t.calls,t.native_calls,t.nonempty_argument_checks,t.local_argument_checks),(9,7,18,9));
    assert_eq!((t.zero_size_arguments,t.native_argument_checks,t.native_local_argument_checks),(9,14,7));
    assert_eq!((t.native_nonempty_results,t.native_local_results),(7,7));
}
#[test]
fn profile_requires_exact_typed_identity_dimensions_and_valid_ranges() {
    let f=function(vec![Op::Local{dst:0,offset:0},call(),Op::Return]);let p=counts(&f);
    let mut bad=p.clone();bad.operations[0]="Local { dst: 0, offset: 1 }".into();assert!(frequencies(&f,&bad).is_err());
    let mut bad=p.clone();bad.name="other".into();assert!(frequencies(&f,&bad).is_err());
    let mut bad=p.clone();bad.jit_blocks.pop();assert!(frequencies(&f,&bad).is_err());
    for end in [0,4] { let mut bad=p.clone();bad.jit_blocks[0]=1;bad.jit_block_ends[0]=end;assert!(frequencies(&f,&bad).is_err()); }
    let mut bad=p.clone();bad.jit_tree_blocks[2]=1;bad.jit_tree_block_ends[2]=2;assert!(frequencies(&f,&bad).is_err());
}
#[test]
fn profile_accounts_both_native_range_kinds_and_rejects_overflow() {
    let f=function(vec![Op::Local{dst:0,offset:0},call(),Op::Return]);let mut p=counts(&f);
    p.jit_blocks[0]=3;p.jit_block_ends[0]=2;p.jit_tree_blocks[1]=7;p.jit_tree_block_ends[1]=3;
    assert_eq!(frequencies(&f,&p).unwrap(),[3,10,7]);
    p.jit_tree_blocks[1]=u64::MAX;assert!(frequencies(&f,&p).is_err());
}
#[test]
fn typed_whole_program_census_keeps_direct_indirect_and_returns_separate() {
    let f=function(vec![Op::Local{dst:0,offset:8},call(),
        Op::CallIndirect{callee:1,args:vec![0],arg_sizes:vec![8],destination:0,result_size:8},Op::Return]);
    let mut p=counts(&f);p.jit_blocks[0]=5;p.jit_block_ends[0]=2;p.interpreted[2]=5;
    p.jit_tree_blocks[3]=5;p.jit_tree_block_ends[3]=4;
    let program=Program{version:VERSION,target:"aarch64-apple-darwin".into(),entry:0,functions:vec![f],data:vec![],statics:vec![],thread_locals:vec![]};
    let report=census(&program,&Profile{functions:vec![p]}).unwrap();
    assert_eq!(report.instructions,20);assert_eq!(report.totals["direct"].native_calls,5);
    assert_eq!(report.totals["indirect"].interpreted_calls,5);
    assert_eq!(report.totals["indirect"].local_argument_checks,5);assert_eq!(report.native_returns,5);
}
