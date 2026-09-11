use super::*;
use crate::{Binary,Slot};
use std::collections::BTreeSet;

#[test]
fn entry_zero_proof_matches_exhaustive_defined_register_paths() {
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
fn entry_zero_proof_requires_reads_before_aliased_writes() {
    let f=|code|Function{name:"entry".into(),frame_size:16,frame_align:16,registers:3,args:vec![],result:Slot{offset:0,size:0},code};
    for op in [Op::Load{dst:0,address:0,size:8},Op::Cast{dst:0,src:0,from:128,to:128,signed:false},
        Op::Binary{dst:0,overflow:1,op:Binary::Add,a:0,b:1,bits:64,signed:false},Op::Select{dst:0,condition:0,yes:1,no:2}] {
        assert!(needs_initial_zeroes(&f(vec![op,Op::Imm{dst:0,value:5},Op::Jump{target:3},Op::Return])));
    }
    // A value defined in a single branch is not an entry definition.
    assert!(needs_initial_zeroes(&f(vec![Op::Imm{dst:0,value:1},Op::Switch{value:0,cases:vec![(0,4)],otherwise:2},
        Op::Imm{dst:1,value:5},Op::Jump{target:4},Op::Assert{value:1,expected:false,message:"join".into()},Op::Return])));
}
