use super::*;
fn needs_initial_zeroes(f: &Function) -> bool { !proves_initialized(f) }
fn block_needs_initial_zeroes(f: &Function, _: &[bool]) -> bool { crate::registers::needs_initial_zeroes_for_inlining(f) }
use crate::{Binary,Slot};
use std::collections::BTreeSet;

#[test]
fn joins_loops_and_unreachable_predecessors_require_all_reachable_paths() {
    let make = |code| Function { name: "join".into(), frame_size: 1, frame_align: 1,
        registers: 3, args: vec![], result: Slot { offset: 0, size: 0 }, code };
    let mut f = make(vec![Op::Imm { dst: 0, value: 0 },
        Op::Switch { value: 0, cases: vec![(0, 4)], otherwise: 2 },
        Op::Imm { dst: 1, value: 2 }, Op::Jump { target: 5 },
        Op::Imm { dst: 1, value: 3 },
        Op::Assert { value: 1, expected: true, message: "join".into() }, Op::Return]);
    assert!(proves_initialized(&f));
    assert!(crate::registers::needs_initial_zeroes_for_inlining(&f));
    f.code[4] = Op::Imm { dst: 2, value: 3 };
    assert!(!proves_initialized(&f));
    // A loop-defined value cannot justify its first read; an unreachable
    // predecessor with no definition cannot invalidate a reachable proof.
    assert!(!proves_initialized(&make(vec![
        Op::Assert { value: 0, expected: false, message: "first".into() },
        Op::Imm { dst: 0, value: 1 }, Op::Jump { target: 0 }])));
    assert!(proves_initialized(&make(vec![Op::Imm { dst: 0, value: 1 },
        Op::Jump { target: 3 }, Op::Jump { target: 3 },
        Op::Assert { value: 0, expected: true, message: "reachable".into() }, Op::Return])));
}

#[test]
fn every_resource_bound_and_work_exhaustion_declines_without_partial_proof() {
    let f = Function { name: "limits".into(), frame_size: 1, frame_align: 1,
        registers: 65, args: vec![], result: Slot { offset: 0, size: 0 }, code: vec![
            Op::Imm { dst: 64, value: 1 }, Op::Jump { target: 2 },
            Op::Assert { value: 64, expected: true, message: "high register".into() }, Op::Return] };
    assert!(proves_initialized(&f));
    for bounds in [Bounds { registers: 64, ..BOUNDS }, Bounds { operations: 3, ..BOUNDS },
        Bounds { blocks: 1, ..BOUNDS }, Bounds { cells: 3, ..BOUNDS },
        Bounds { edges: 0, ..BOUNDS }, Bounds { work: 0, ..BOUNDS }] {
        assert_eq!(prove(&f, bounds), None);
    }
    let first = (0..1000).find(|&work| prove(&f, Bounds { work, ..BOUNDS }) == Some(true)).unwrap();
    for work in 0..first { assert_eq!(prove(&f, Bounds { work, ..BOUNDS }), None); }
}

#[test]
fn cfg_proof_matches_exhaustive_defined_register_paths() {
    // Independent graph oracle: explore every branch with a three-bit defined
    // set. The read/write masks below are specified alongside each operation,
    // rather than obtained from the production register visitor.
    let choices=vec![
        (Op::Imm{dst:0,value:1},0,1),(Op::Imm{dst:1,value:2},0,2),(Op::Imm{dst:2,value:3},0,4),
        (Op::Cast{dst:0,src:1,from:64,to:64,signed:false},2,1),
        (Op::Binary{dst:0,overflow:1,op:Binary::Add,a:1,b:2,bits:64,signed:false},6,3),
        (Op::Load{dst:0,address:1,size:8},2,1),(Op::Store{address:0,src:1,size:8},3,0),
        (Op::Copy{dst:0,src:1,size:8},3,0),(Op::Call{function:0,args:vec![0],destination:1},3,0),
        (Op::Select{dst:2,condition:0,yes:1,no:2},7,4),
        (Op::Jump{target:0},0,0),(Op::Jump{target:4},0,0),
        (Op::Switch{value:0,cases:vec![(0,1)],otherwise:4},1,0),(Op::Return,0,0),
    ];
    let mut improved=0;let mut checked=0;
    for mut shape in 0..choices.len().pow(4) {
        let mut ops=vec![];let mut masks=vec![];
        for _ in 0..4 {let (op,read,write)=&choices[shape%choices.len()];shape/=choices.len();ops.push(op.clone());masks.push((*read,*write));}
        ops.push(Op::Return);masks.push((0,0));
        let f=Function{name:"proof-oracle".into(),frame_size:16,frame_align:16,registers:3,args:vec![],result:Slot{offset:0,size:0},code:ops};
        let needed=needs_initial_zeroes(&f);let old=block_needs_initial_zeroes(&f,&[]);assert!(old||!needed);
        if old&&!needed {improved+=1;}
        if !needed {
            let mut todo=vec![(0usize,0u8)];let mut visited=BTreeSet::new();
            while let Some((pc,defined))=todo.pop() {
                if !visited.insert((pc,defined)) {continue;}
                let (read,write)=masks[pc];assert_eq!(read&!defined,0,"uninitialized read pc={pc} code={:?}",f.code);
                let next=defined|write;
                match &f.code[pc] {
                    Op::Jump{target}=>todo.push((*target,next)),
                    Op::Switch{cases,otherwise,..}=>{todo.push((*otherwise,next));for (_,target) in cases{todo.push((*target,next));}},
                    Op::Return=>{},_=>todo.push((pc+1,next)),
                }
            }
        }
        checked+=1;
    }
    assert_eq!(checked,38_416);assert!(improved>0);
}

#[test]
fn cfg_proof_requires_reads_before_aliased_writes() {
    let f=|code|Function{name:"entry".into(),frame_size:16,frame_align:16,registers:3,args:vec![],result:Slot{offset:0,size:0},code};
    for op in [Op::Load{dst:0,address:0,size:8},Op::Cast{dst:0,src:0,from:128,to:128,signed:false},
        Op::Binary{dst:0,overflow:1,op:Binary::Add,a:0,b:1,bits:64,signed:false},Op::Select{dst:0,condition:0,yes:1,no:2}] {
        assert!(needs_initial_zeroes(&f(vec![op,Op::Imm{dst:0,value:5},Op::Jump{target:3},Op::Return])));
    }
    // A value defined in a single branch is not an entry definition.
    assert!(needs_initial_zeroes(&f(vec![Op::Imm{dst:0,value:1},Op::Switch{value:0,cases:vec![(0,4)],otherwise:2},
        Op::Imm{dst:1,value:5},Op::Jump{target:4},Op::Assert{value:1,expected:false,message:"join".into()},Op::Return])));
}
