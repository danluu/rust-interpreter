//! Execute the one-body aggregate ABI against full bytes, exact PCs and canaries.
use super::*;
use crate::{Program,Slot,VERSION};

fn program(code:Vec<Op>,frame:usize,args:Vec<Slot>,result:Slot)->Program {
    Program{version:VERSION,target:"aarch64-apple-darwin".into(),entry:0,data:vec![],statics:vec![],thread_locals:vec![],
        functions:vec![Function{name:"native aggregate control".into(),frame_size:frame,frame_align:16,registers:8,args,result,code}]}
}
fn local(dst:u32,offset:usize)->Op {Op::Local{dst,offset}}
fn plan(p:&Program)->Plan {
    crate::validate(p).unwrap();
    let memory=crate::proof::aggregate_memory_plan(p,0,&mut crate::proof::MAX_GLOBAL_WORK.clone(),true);
    lower_aggregate(&p.functions[0],&memory,1_000_000).unwrap()
}
fn variants(p:&Program,plan:&Plan,profiled:bool)->[Native;2] {
    [false,true].map(|call| {
        let emitted=if call {tests::call_wrapper_body(plan,profiled,p.functions[0].args.len(),emit_call_aggregate(plan,profiled).unwrap())}
            else {emit_aggregate(plan,profiled).unwrap()};
        let mut code=memory::Code::reserve(MAX_CODE_BYTES).unwrap();assert_eq!(code.append(&emitted.words).unwrap(),0);
        Native{code,emitted,argument_widths:p.functions[0].args.iter().map(|s|s.size).collect(),frame_size:p.functions[0].frame_size.max(1)}
    })
}
#[repr(C)]
struct Guarded {before:[u128;2],output:Output,after:[u128;2]}
fn check(p:&Program,plan:&Plan,native:&Native,args:&[u128],base:usize,budget:usize)->Option<Vec<u8>> {
    let expected=plan.evaluate(args,base,budget,&p.functions[0].name);
    let mut guarded=Guarded{before:[0x123456789abcdef;2],
        output:Output{value:u128::MAX,tail:[u128::MAX;3],steps:u64::MAX,visited:[u64::MAX;8]},after:[0xfedcba987654321;2]};
    let before=guarded.output.clone();
    let actual=unsafe {native.code.tree_abi_probe(0,[args.as_ptr() as usize,base,
        std::ptr::from_mut(&mut guarded.output) as usize,budget,0x123,0x456,0x789,0xabc])};
    assert_eq!(guarded.before,[0x123456789abcdef;2]);assert_eq!(guarded.after,[0xfedcba987654321;2]);
    assert_eq!([actual[1],actual[2],actual[3],actual[4],actual[7],actual[8],actual[9],actual[10],actual[11],actual[12]],
        [0x1357,0x2468,0x3579,0x468a,0x579b,0x68ac,0x79bd,0x8ace,0x9bdf,0xace0]);assert_eq!(actual[5],actual[6]);
    let output=guarded.output;
    if actual[0]==1 {
        assert!(budget<plan.maximum_steps || expected.is_err(),"unexpected aggregate decline");
        assert_eq!(output.bytes(),before.bytes(),"failed body must not publish a result");
        if budget<plan.maximum_steps {assert_eq!(output,before,"short admission must not touch private output");}
        return None;
    }
    assert_eq!(actual[0],0,"private status/ABI corruption");
    let expected=expected.unwrap();assert_eq!(&output.bytes()[..plan.result_size],expected.bytes);
    assert_eq!(output.steps as usize,expected.pcs.len());
    let mut visited=[0;8];for pc in expected.pcs {visited[pc/64]|=1u64<<(pc%64);}
    assert_eq!(output.visited,if native.emitted.profiled {visited} else {[u64::MAX;8]});
    if plan.result_size!=0 {
        let end=plan.result_size.div_ceil(16)*16;
        assert_eq!(&output.bytes()[plan.result_size..end],vec![0;end-plan.result_size]);
        assert_eq!(&output.bytes()[end..],vec![255;64-end]);
    }
    Some(expected.bytes)
}

#[test]
fn every_aggregate_width_preserves_ordered_inputs_and_private_abi() {
    let args:[u128;3]=[u128::MAX,0x0123456789abcdef,0xfedcba9876543210_0102030405060708];
    for width in 0..=64 {
        let p=program(vec![Op::Return],80,vec![Slot{offset:0,size:16},Slot{offset:8,size:8},Slot{offset:32,size:16}],Slot{offset:0,size:width});
        let plan=plan(&p);let mut expected=vec![0;80];
        for (slot,value) in p.functions[0].args.iter().zip(args) {expected[slot.offset..slot.offset+slot.size].copy_from_slice(&value.to_le_bytes()[..slot.size]);}
        for profiled in [false,true] {for native in variants(&p,&plan,profiled) {
            assert!(check(&p,&plan,&native,&args,16,0).is_none());
            assert_eq!(check(&p,&plan,&native,&args,16,1).unwrap(),expected[..width]);
        }}
    }
}

#[test]
fn overlapping_copies_match_independent_complete_byte_oracle() {
    let args:[u128;4]=[0x0001020304050607_08090a0b0c0d0e0f,0x1011121314151617_18191a1b1c1d1e1f,
        0x2021222324252627_28292a2b2c2d2e2f,0x3031323334353637_38393a3b3c3d3e3f];
    let mut cases=0;
    for size in [0,1,7,8,15,16,17,31,32,40,48,63,64] {for src in [0,1,8,16,31,32] {for dst in [0,1,8,16,31,32] {
        let p=program(vec![local(0,src),local(1,dst),Op::Copy{src:0,dst:1,size},Op::Return],96,
            (0..4).map(|i|Slot{offset:i*16,size:16}).collect(),Slot{offset:0,size:64});
        let plan=plan(&p);let mut expected=vec![0;96];
        for (i,v) in args.iter().enumerate() {expected[i*16..(i+1)*16].copy_from_slice(&v.to_le_bytes());}
        let source=expected[src..src+size].to_vec();expected[dst..dst+size].copy_from_slice(&source);
        for profiled in [false,true] {for native in variants(&p,&plan,profiled) {
            assert_eq!(check(&p,&plan,&native,&args,16,4).unwrap(),expected[..64]);
        }}
        cases+=1;
    }}}
    assert_eq!(cases,468);
}

#[test]
fn aggregate_branch_joins_and_distinct_return_paths_preserve_budget_and_profiles() {
    let p=program(vec![local(0,64),Op::Load{dst:1,address:0,size:16},
        Op::Switch{value:1,cases:vec![(1u128<<100,6)],otherwise:3},
        local(2,0),Op::Store{address:2,src:1,size:16},Op::Jump{target:8},
        local(2,32),Op::Store{address:2,src:1,size:16},Op::Return],80,
        vec![Slot{offset:64,size:16}],Slot{offset:0,size:63});
    let q=program(vec![Op::Jump{target:6},local(0,0),Op::Store{address:0,src:1,size:16},Op::Return,
        local(0,32),Op::Return,local(0,64),Op::Load{dst:1,address:0,size:16},
        Op::Switch{value:1,cases:vec![(0,1)],otherwise:4}],80,
        vec![Slot{offset:64,size:16}],Slot{offset:0,size:40});
    for p in [p,q] {
        let plan=plan(&p);assert!(plan.success_steps.is_none());
        for profiled in [false,true] {for native in variants(&p,&plan,profiled) {
            for input in [0,1,1u128<<100,(1u128<<100)|1] {for budget in 0..=plan.maximum_steps+1 {
                check(&p,&plan,&native,&[input],16,budget);
            }}
        }}
    }
    let mut code=vec![Op::Imm{dst:0,value:1};511];code.push(Op::Return);
    let p=program(code,64,vec![],Slot{offset:0,size:64});let plan=plan(&p);
    for profiled in [false,true] {for native in variants(&p,&plan,profiled) {for budget in [0,1,64,511,512,513] {
        check(&p,&plan,&native,&[],16,budget);
    }}}
}

#[test]
fn aggregate_dead_division_late_assertions_and_traps_discard_private_results() {
    let mut cases=vec![];
    for divisor in [0,1,7] {for expected in [false,true] {
        cases.push(program(vec![Op::Imm{dst:0,value:9},local(4,16),Op::Store{address:4,src:0,size:16},
            Op::Imm{dst:1,value:divisor},Op::Binary{dst:2,overflow:3,op:Binary::Div,a:0,b:1,bits:64,signed:false},
            Op::Assert{value:1,expected,message:"late condition".into()},Op::Return],64,vec![],Slot{offset:0,size:64}));
    }}
    cases.push(program(vec![Op::Trap{message:"terminal".into()}],64,vec![],Slot{offset:0,size:64}));
    for p in cases {let plan=plan(&p);
        for profiled in [false,true] {for native in variants(&p,&plan,profiled) {for budget in 0..=plan.maximum_steps+1 {
            check(&p,&plan,&native,&[],16,budget);
        }}}
    }
}

#[test]
fn maximum_argument_count_wide_frame_and_local_address_bits_are_preserved() {
    let p=program(vec![local(0,1000),local(1,968),Op::Store{address:1,src:0,size:8},Op::Return],1024,
        (0..64).map(|i|Slot{offset:i*16,size:16}).collect(),Slot{offset:960,size:64});let plan=plan(&p);
    let args:Vec<u128>=(0..64).map(|i|u128::MAX-i).collect();
    for profiled in [false,true] {for native in variants(&p,&plan,profiled) {
        for base in [16,0x1000,usize::MAX-1024] {
            let bytes=check(&p,&plan,&native,&args,base,4).unwrap();
            assert_eq!(&bytes[8..16],&(base as u64+1000).to_le_bytes());
        }
        assert!(native.attempt(&args[..63],16,4).is_err());
        assert!(native.attempt(&args,usize::MAX,4).is_err());
    }}
}

#[test]
fn malformed_aggregate_result_shape_declines_before_publication() {
    let p=program(vec![Op::Return],64,vec![],Slot{offset:0,size:64});
    let mut bad=plan(&p);bad.result_size=65;
    assert!(matches!(emit_call_aggregate(&bad,false),Err("native_aggregate_result_limit")));
    let mut bad=plan(&p);let Effect::ReturnLanes(lanes)=&mut bad.effects[0] else {panic!()};lanes.pop();
    assert!(matches!(emit_call_aggregate(&bad,false),Err("native_aggregate_return_shape")));
    let mut bad=plan(&p);let Effect::ReturnLanes(lanes)=&bad.effects[0] else {panic!()};bad.effects[0]=Effect::Return(lanes[0]);
    assert!(matches!(emit_call_aggregate(&bad,false),Err("native_aggregate_return_shape")));
}
