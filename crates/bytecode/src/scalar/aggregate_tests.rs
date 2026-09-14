use super::*;
use crate::{Engine,Limits,Program,Slot,VERSION};
fn program(code:Vec<Op>,frame:usize,args:Vec<Slot>,result:Slot)->Program {
    Program{version:VERSION,target:"aarch64-apple-darwin".into(),entry:0,data:vec![],statics:vec![],thread_locals:vec![],
        functions:vec![Function{name:"aggregate control".into(),frame_size:frame,frame_align:8,registers:8,args,result,code}]}
}
fn local(dst:u32,offset:usize)->Op {Op::Local{dst,offset}}
fn plan(p:&Program,zeroed:bool)->Result<Aggregate,&'static str> {
    crate::validate(p).unwrap();
    let memory=crate::proof::aggregate_memory_plan(p,0,&mut crate::proof::MAX_GLOBAL_WORK.clone(),zeroed);
    Aggregate::new(&p.functions[0],&memory,1_000_000)
}
fn compare(p:&Program,a:&Aggregate,args:&[u128],budget:usize)->Option<Vec<u8>> {
    let f=&p.functions[0];let base=(p.data.len().max(16)+f.frame_align-1)&!(f.frame_align-1);
    let observed=a.evaluate(args,base,budget,&f.name);let mut bytes=vec![];let mut first_error=None;let mut offset=0;
    for (size,_) in &a.lanes {
        let mut projected=p.clone();projected.functions[0].result=Slot{offset:f.result.offset+offset,size:*size};
        let ordinary=crate::execute_profiled(&projected,args,Limits{instructions:budget as u64,..Limits::default()},Engine::Interpreter);
        match ordinary {
            Ok((e,profile))=>{
                let (_,pcs)=observed.as_ref().unwrap();let mut counts=vec![0u64;f.code.len()];for pc in pcs {counts[*pc]+=1;}
                assert_eq!(counts,profile.functions[0].interpreted);assert_eq!(pcs.len() as u64,e.instructions);
                bytes.extend_from_slice(&e.value.to_le_bytes()[..*size]);
            },
            Err(error)=>{assert_eq!(observed.as_ref().unwrap_err(),&error);if let Some(old)=&first_error {assert_eq!(old,&error);}first_error=Some(error);},
        }
        offset+=size;
    }
    if first_error.is_some() {None} else {assert_eq!(observed.unwrap().0,bytes);Some(bytes)}
}

#[test]
fn every_result_width_preserves_ordered_arguments_and_zero_bytes() {
    for width in 0..=64 {
        let p=program(vec![Op::Return],80,vec![Slot{offset:0,size:16},Slot{offset:8,size:8},Slot{offset:32,size:16}],Slot{offset:0,size:width});
        let args:[u128;3]=[u128::MAX,0x123456789abcdef0,0xfedcba9876543210_0102030405060708];
        let mut expected=vec![0;80];
        for (slot,value) in p.functions[0].args.iter().zip(args) {expected[slot.offset..slot.offset+slot.size].copy_from_slice(&value.to_le_bytes()[..slot.size]);}
        let a=plan(&p,true).unwrap();assert_eq!(compare(&p,&a,&args,1).unwrap(),expected[..width]);assert!(compare(&p,&a,&args,0).is_none());
    }
}

#[test]
fn independent_byte_oracle_preserves_large_overlapping_copies() {
    let args:[u128;4]=[0x0001020304050607_08090a0b0c0d0e0f,0x1011121314151617_18191a1b1c1d1e1f,
              0x2021222324252627_28292a2b2c2d2e2f,0x3031323334353637_38393a3b3c3d3e3f];
    for size in [0,1,7,8,15,16,17,31,32,40,48,63,64] {for src in [0,1,8,16,31,32] {for dst in [0,1,8,16,31,32] {
        let p=program(vec![local(0,src),local(1,dst),Op::Copy{src:0,dst:1,size},Op::Return],96,
            (0..4).map(|i|Slot{offset:i*16,size:16}).collect(),Slot{offset:0,size:64});
        let mut expected=vec![0;96];for (i,value) in args.iter().enumerate() {expected[i*16..(i+1)*16].copy_from_slice(&value.to_le_bytes());}
        let source=expected[src..src+size].to_vec();expected[dst..dst+size].copy_from_slice(&source);
        let a=plan(&p,true).unwrap();assert_eq!(compare(&p,&a,&args,4).unwrap(),expected[..64]);
    }}}
}

#[test]
fn branch_padding_and_full_width_conditions_preserve_every_budget() {
    let p=program(vec![local(0,64),Op::Load{dst:1,address:0,size:16},
        Op::Switch{value:1,cases:vec![(1u128<<100,6)],otherwise:3},
        local(2,0),Op::Store{address:2,src:1,size:16},Op::Jump{target:8},
        local(2,32),Op::Store{address:2,src:1,size:16},Op::Return],80,
        vec![Slot{offset:64,size:16}],Slot{offset:0,size:64});
    assert!(plan(&p,false).is_err());let a=plan(&p,true).unwrap();
    for input in [0,1,1u128<<100,(1u128<<100)|1] {
        let mut expected=vec![0;64];let offset=if input==1u128<<100 {32} else {0};
        expected[offset..offset+16].copy_from_slice(&input.to_le_bytes());
        assert_eq!(compare(&p,&a,&[input],100).unwrap(),expected);
        for budget in 0..=10 {compare(&p,&a,&[input],budget);}
    }
}

#[test]
fn dead_fallible_operations_and_late_assertions_are_not_lost_by_projection() {
    for divisor in [0,1,7] {
        let p=program(vec![Op::Imm{dst:0,value:9},Op::Imm{dst:1,value:divisor},
            Op::Binary{dst:2,overflow:3,op:Binary::Div,a:0,b:1,bits:64,signed:false},
            Op::Assert{value:1,expected:false,message:"late condition".into()},Op::Return],64,vec![],Slot{offset:0,size:64});
        let a=plan(&p,true).unwrap();for budget in 0..=6 {compare(&p,&a,&[],budget);}
    }
    let p=program(vec![Op::Trap{message:"terminal".into()}],64,vec![],Slot{offset:0,size:64});
    let a=plan(&p,true).unwrap();for budget in 0..=2 {compare(&p,&a,&[],budget);}
}

#[test]
fn external_reads_writes_and_nested_calls_remain_ineligible() {
    for operation in [Op::Load{dst:2,address:1,size:8},Op::Store{address:1,src:2,size:8}] {
        let p=program(vec![local(0,64),Op::Load{dst:1,address:0,size:8},operation,Op::Return],72,
            vec![Slot{offset:64,size:8}],Slot{offset:0,size:64});
        for zeroed in [false,true] {assert!(plan(&p,zeroed).is_err());}
    }
    let p=program(vec![local(0,0),Op::Call{function:0,args:vec![],destination:0},Op::Return],64,vec![],Slot{offset:0,size:64});
    assert!(plan(&p,true).is_err());
}

#[test]
fn aggregate_bounds_and_work_exhaustion_decline() {
    let mut p=program(vec![Op::Return],1024,vec![],Slot{offset:0,size:64});assert!(plan(&p,true).is_ok());
    p.functions[0].frame_size=1025;assert!(plan(&p,true).is_err());p.functions[0].frame_size=1024;
    p.functions[0].result.size=65;assert!(plan(&p,true).is_err());p.functions[0].result.size=64;
    p.functions[0].registers=513;assert!(plan(&p,true).is_err());p.functions[0].registers=8;
    let memory=crate::proof::aggregate_memory_plan(&p,0,&mut crate::proof::MAX_GLOBAL_WORK.clone(),true);
    assert!(Aggregate::new(&p.functions[0],&memory,0).is_err());
    assert!(!crate::proof::aggregate_memory_plan(&p,0,&mut 0,true).eligible);
    p.functions[0].args=vec![Slot{offset:0,size:32}];assert!(plan(&p,true).is_err());
}

#[test]
fn initialized_policy_and_legacy_limits_remain_separate() {
    let p=program(vec![Op::Return],64,(0..4).map(|i|Slot{offset:i*16,size:16}).collect(),Slot{offset:0,size:64});
    assert!(plan(&p,false).is_ok());assert!(!crate::proof::memory_plan(&p,0,&mut crate::proof::MAX_GLOBAL_WORK.clone()).eligible);
    for width in [0,1,2,4,8,16] {
        let p=program(vec![Op::Return],16,vec![Slot{offset:0,size:16}],Slot{offset:0,size:width});
        let old=crate::proof::memory_plan(&p,0,&mut crate::proof::MAX_GLOBAL_WORK.clone());
        let wide=crate::proof::aggregate_memory_plan(&p,0,&mut crate::proof::MAX_GLOBAL_WORK.clone(),false);
        assert!(old.eligible && wide.eligible);assert_eq!(old.accesses,wide.accesses);assert_eq!(old.work,wide.work);
        let a=plan(&p,false).unwrap();assert_eq!(compare(&p,&a,&[u128::MAX],1).unwrap(),vec![255;width]);
    }
}

#[test]
fn local_pointer_results_and_malformed_return_annotations_are_checked() {
    let p=program(vec![local(0,1000),local(1,24),Op::Store{address:1,src:0,size:8},Op::Return],1024,vec![],Slot{offset:0,size:64});
    let a=plan(&p,true).unwrap();let bytes=compare(&p,&a,&[],4).unwrap();assert_eq!(&bytes[24..32],&(1016u64).to_le_bytes());
    let mut memory=crate::proof::aggregate_memory_plan(&p,0,&mut crate::proof::MAX_GLOBAL_WORK.clone(),true);
    memory.accesses.last_mut().unwrap().reads[0].size=16;
    assert!(Aggregate::new(&p.functions[0],&memory,1_000_000).is_err());
}
