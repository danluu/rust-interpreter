use super::*;
use crate::{Slot, VERSION};

fn program(code: Vec<Op>) -> Program {
    let caller = Function { name:"caller".into(), frame_size:64, frame_align:8, registers:4,
        args:vec![], result:Slot{offset:0,size:0}, code };
    let callee = Function { name:"callee".into(), frame_size:16, frame_align:8, registers:0,
        args:vec![Slot{offset:0,size:8}],result:Slot{offset:0,size:0},code:vec![Op::Return] };
    Program { version:VERSION,target:"aarch64-apple-darwin".into(),entry:0,
        functions:vec![caller,callee],data:vec![],statics:vec![],thread_locals:vec![] }
}
fn call() -> Op { Op::Call { function:1,args:vec![0],destination:1 } }

#[test]
fn calls_and_memory_writes_preserve_hints_but_register_writes_kill_them() {
    let p=program(vec![Op::Local{dst:0,offset:8},call(),Op::Store{address:0,src:1,size:8},call(),
        Op::Load{dst:0,address:0,size:8},call(),Op::Return]);
    crate::validate(&p).unwrap();
    assert_eq!(collect(&p.functions[0],&p),BTreeMap::from([(1,vec![Some(8)]),(3,vec![Some(8)])]));
}
#[test]
fn skipped_definitions_merges_and_backedges_keep_unknown_addresses() {
    for code in [vec![Op::Jump{target:2},Op::Local{dst:0,offset:8},call(),Op::Return],
        vec![Op::Local{dst:0,offset:8},Op::Switch{value:1,cases:vec![(0,3)],otherwise:2},
            Op::Local{dst:0,offset:8},call(),Op::Return],
        vec![Op::Local{dst:0,offset:8},call(),Op::Load{dst:0,address:1,size:8},Op::Jump{target:1}]] {
        let p=program(code);crate::validate(&p).unwrap();assert!(collect(&p.functions[0],&p).is_empty());
    }
}
#[test]
fn target_width_addition_alias_order_and_extent_limits_are_conservative() {
    let mut p=program(vec![Op::Local{dst:0,offset:8},Op::Imm{dst:1,value:(1u128<<100)+16},
        Op::Binary{dst:0,overflow:2,op:Binary::Add,a:0,b:1,bits:64,signed:false},call(),Op::Return]);
    crate::validate(&p).unwrap();assert_eq!(collect(&p.functions[0],&p)[&3],vec![Some(24)]);
    p.functions[0].code[2]=Op::Binary{dst:0,overflow:0,op:Binary::Add,a:0,b:1,bits:64,signed:false};
    assert!(collect(&p.functions[0],&p).is_empty());
    for offset in [57,64] {
        let p=program(vec![Op::Local{dst:0,offset},call(),Op::Return]);
        assert!(collect(&p.functions[0],&p).is_empty());
    }
    let mut p=program(vec![Op::Local{dst:0,offset:8},call(),Op::Return]);
    p.functions[1].args[0].size=0;assert!(collect(&p.functions[0],&p).is_empty());
}
#[test]
fn exhausted_analysis_discards_partial_hints() {
    let p=program(vec![Op::Local{dst:0,offset:8},call(),call(),Op::Return]);
    assert_eq!(collect(&p.functions[0],&p).len(),2);
    // Register initialization + four op visits + first argument fits; the
    // second argument exceeds this limit. No partially collected result escapes.
    assert!(collect_with_work(&p.functions[0],&p,9).is_empty());
}
