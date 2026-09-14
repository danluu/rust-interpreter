use super::*;
use crate::{Program,Slot,VERSION};

pub(super) fn lower_code(code:Vec<Op>)->Plan {
    let p=Program{version:VERSION,target:"aarch64-apple-darwin".into(),entry:0,data:vec![],statics:vec![0;64],thread_locals:vec![],
        functions:vec![crate::Function{name:"entry guards".into(),frame_size:16,frame_align:8,registers:12,
            args:vec![Slot{offset:0,size:8},Slot{offset:8,size:8}],result:Slot{offset:0,size:0},code}]};
    crate::validate(&p).unwrap();
    let memory=crate::proof::memory_plan_transaction(&p,0,&mut crate::proof::MAX_GLOBAL_WORK.clone());
    crate::scalar_ir::lower(&p.functions[0],&memory,250_000).unwrap()
}
pub(super) fn prefix()->Vec<Op> {vec![Op::Local{dst:0,offset:0},Op::Load{dst:1,address:0,size:8},
    Op::Local{dst:2,offset:8},Op::Load{dst:3,address:2,size:8},Op::Imm{dst:4,value:19}]}

#[test]
fn entry_addresses_preserve_full_low_word_wrapping_semantics() {
    for offset in [0,8,u64::MAX-7] {
        let mut code=prefix();code.extend([Op::Imm{dst:5,value:offset as u128},
            Op::Binary{dst:6,overflow:7,op:Binary::Add,a:1,b:5,bits:64,signed:false},
            Op::Store{address:6,src:4,size:8},Op::Return]);
        let plan=lower_code(code);let classified=classify(&plan).unwrap();assert_eq!(classified.ranges.len(),1);
        let address=classified.ranges[0].address;assert_eq!(address,Address{root:Root::Input(0),offset});
        for input in [0u128,1,u64::MAX as u128,1<<63,u128::MAX] {
            let (expected,_)=crate::binary(Binary::Add,input,offset as u128,64,false).unwrap();
            assert_eq!((input as u64).wrapping_add(address.offset),expected as u64);
        }
    }
}

#[test]
fn memory_derived_and_narrow_cast_addresses_decline() {
    let mut code=prefix();code.extend([Op::Load{dst:5,address:1,size:8},Op::Store{address:5,src:4,size:8},Op::Return]);
    assert_eq!(classify(&lower_code(code)).err(),Some("entry_address_memory_root"));
    let mut code=prefix();code.extend([Op::Cast{dst:5,src:1,from:64,to:32,signed:false},
        Op::Store{address:5,src:4,size:8},Op::Return]);
    assert_eq!(classify(&lower_code(code)).err(),Some("entry_address_non_affine_root"));
}

#[test]
fn pre_store_faults_are_allowed_but_post_store_faults_decline() {
    for split in [false,true] {for before in [false,true] {
        let mut code=prefix();let check=Op::Assert{value:3,expected:true,message:"condition".into()};
        let write=Op::Store{address:1,src:4,size:8};
        code.push(if before {check.clone()} else {write.clone()});
        if split {code.push(Op::Jump{target:code.len()+1});}
        code.extend([if before {write} else {check},Op::Return]);
        assert_eq!(classify(&lower_code(code)).is_ok(),before);
    }}
}

pub(super) fn abstract_diamond(stores:u8,faults:u8,reverse:bool)->Plan {
    let ids=if reverse {[0,3,2,1]} else {[0,1,2,3]};
    let mut nodes=vec![Node{value:Value::Input(0),width:8,pc:None},Node{value:Value::Constant(19),width:1,pc:None}];
    let mut computations=vec![vec![];4];let mut effects=vec![Effect::None;4];
    let mut blocks:Vec<_>=(0..4).map(|pc|Block{start:pc,end:pc+1,successors:vec![],predecessors:vec![],phis:vec![]}).collect();
    blocks[ids[0]].successors=vec![ids[1],ids[2]];blocks[ids[1]].successors=vec![ids[3]];blocks[ids[2]].successors=vec![ids[3]];
    for logical in 0..4 {
        let pc=ids[logical];
        if stores&(1<<logical)!=0 {
            computations[pc].push(nodes.len());nodes.push(Node{value:Value::Write{address:0,value:1,size:8},width:0,pc:Some(pc)});
        }
        if faults&(1<<logical)!=0 {effects[pc]=Effect::Assert{value:0,expected:true,message:"abstract condition".into()};}
    }
    let live=vec![true;nodes.len()];
    Plan{nodes,blocks,at:vec![0,1,2,3],computations,effects,live,reachable:vec![true;4],
        maximum_steps:3,success_steps:Some(3),result_size:0,work:0}
}

#[test]
fn complete_cfg_rule_matches_forward_paths_with_permuted_block_order() {
    for stores in 0..16u8 {for faults in 0..16u8 {for reverse in [false,true] {
        let expected=[[0,1,3],[0,2,3]].into_iter().all(|path| {
            let mut wrote=false;
            path.into_iter().all(|block| {wrote|=stores&(1<<block)!=0; !(wrote && faults&(1<<block)!=0)})
        });
        assert_eq!(no_failure_after_write(&abstract_diamond(stores,faults,reverse)).is_ok(),expected,
            "stores={stores}, faults={faults}, reverse={reverse}");
    }}}
}

#[test]
fn computation_order_within_one_pc_controls_division_decline() {
    let mut plan=abstract_diamond(1,0,false);let write=plan.computations[0][0];let division=plan.nodes.len();
    plan.nodes.push(Node{value:Value::Binary{a:1,b:0,op:Binary::Div,bits:64,signed:false,overflow:false},width:8,pc:Some(0)});
    plan.live.push(true);plan.computations[0]=vec![division,write];assert!(no_failure_after_write(&plan).is_ok());
    plan.computations[0]=vec![write,division];assert_eq!(no_failure_after_write(&plan).err(),Some("entry_division_after_write"));
}

#[test]
fn reads_and_writes_merge_permissions_without_losing_widths() {
    let mut code=prefix();code.extend([Op::Load{dst:5,address:1,size:8},
        Op::Store{address:1,src:5,size:4},Op::Store{address:1,src:4,size:8},Op::Return]);
    let result=classify(&lower_code(code)).unwrap();assert_eq!((result.reads,result.writes),(1,2));
    assert_eq!(result.ranges.iter().map(|r|(r.size,r.write)).collect::<Vec<_>>(),[(4,true),(8,true)]);
}

#[test]
fn zero_width_and_excessive_store_and_range_counts_decline() {
    let mut plan=abstract_diamond(1,0,false);let write=plan.computations[0][0];
    plan.nodes[write].value=Value::Write{address:0,value:1,size:0};assert_eq!(classify(&plan).err(),Some("entry_range_width"));
    plan.nodes[write].value=Value::Write{address:0,value:1,size:8};
    for _ in 1..17 {let id=plan.nodes.len();plan.nodes.push(plan.nodes[write].clone());plan.live.push(true);plan.computations[0].push(id);}
    assert_eq!(classify(&plan).err(),Some("entry_store_limit"));
    let mut plan=abstract_diamond(1,0,false);
    for i in 0..MAX_RANGES {let id=plan.nodes.len();
        plan.nodes.push(Node{value:Value::Constant((i as u128+1)*16),width:8,pc:None});
        plan.nodes.push(Node{value:Value::Read{address:id,size:8},width:8,pc:Some(0)});
        plan.live.extend([true,true]);plan.computations[0].push(id+1);
    }
    assert_eq!(classify(&plan).err(),Some("entry_range_limit"));
}
