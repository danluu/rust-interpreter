use super::*;
use crate::{Program,Slot,VERSION,Limits,Engine};

fn program(code:Vec<Op>,frame:usize,args:Vec<Slot>,result:Slot) -> Program {
    Program{version:VERSION,target:"aarch64-apple-darwin".into(),entry:0,data:vec![],statics:vec![],thread_locals:vec![],
        functions:vec![Function{name:"scalar control".into(),frame_size:frame,frame_align:8,registers:8,args,result,code}]}
}
fn local(dst:u32,offset:usize)->Op {Op::Local{dst,offset}}
fn load(dst:u32,address:u32,size:u8)->Op {Op::Load{dst,address,size}}
fn store(address:u32,src:u32,size:u8)->Op {Op::Store{address,src,size}}
fn plan(p:&Program)->Plan {
    crate::validate(p).unwrap();let memory=crate::proof::memory_plan(p,0,&mut crate::proof::MAX_GLOBAL_WORK.clone());
    assert!(memory.eligible,"{:?}",memory.decline);lower(&p.functions[0],&memory,250_000).unwrap()
}
fn compare(p:&Program,plan:&Plan,args:&[u128],budget:usize) {
    let f=&p.functions[0];let base=(p.data.len().max(16)+f.frame_align-1)&!(f.frame_align-1);
    let scalar=plan.evaluate(args,base,budget,&f.name);
    let original=crate::execute_profiled(p,args,Limits{instructions:budget as u64,..Limits::default()},Engine::Interpreter);
    match (scalar,original) {
        (Ok(s),Ok((e,profile)))=>{
            assert_eq!(s.value,e.value);assert_eq!(s.pcs.len() as u64,e.instructions);
            let mut counts=vec![0u64;f.code.len()];for pc in s.pcs {counts[pc]+=1;}
            assert_eq!(counts,profile.functions[0].interpreted);
        },
        (Err(s),Err(e))=>assert_eq!(s,e),
        (s,e)=>panic!("scalar {s:?}, original {e:?}"),
    }
}

#[test]
fn scalar_byte_oracle_preserves_2187_overlapping_copies() {
    let mut cases=0;
    for src in 0..=8 {for dst in 0..=8 {for size in 0..=8 {
        let p=program(vec![local(0,src),local(1,dst),Op::Copy{src:0,dst:1,size},
            local(2,0),load(3,2,16),Op::Return],16,vec![Slot{offset:0,size:16}],Slot{offset:0,size:16});
        let plan=plan(&p);
        for input in [0,u128::MAX,0x0123456789abcdef_fedcba9876543210] {compare(&p,&plan,&[input],6);cases+=1;}
    }}}
    assert_eq!(cases,2187);
}

#[test]
fn scalar_cfg_joins_and_every_original_budget_preserve_profiles() {
    let p=program(vec![local(0,0),local(1,8),load(2,0,8),load(3,1,8),
        Op::Switch{value:2,cases:vec![(0,5)],otherwise:8},
        Op::Binary{dst:4,overflow:5,op:Binary::Add,a:2,b:3,bits:64,signed:false},store(1,4,8),Op::Jump{target:10},
        Op::Unary{dst:4,op:Unary::Not,src:3,bits:64},store(0,4,8),
        Op::Select{dst:6,condition:2,yes:4,no:3},Op::Cast{dst:6,src:6,from:8,to:64,signed:true},store(1,6,8),Op::Return],
        16,vec![Slot{offset:0,size:8},Slot{offset:8,size:8}],Slot{offset:0,size:16});
    let plan=plan(&p);assert!(summary(&Ok(plan.clone())).live_phis>0);
    for args in [[0,255],[1,23],[u64::MAX as u128,128]] {for budget in 0..=15 {compare(&p,&plan,&args,budget);}}
    // Input stores are ordered even when ABI slots overlap.
    let p=program(vec![Op::Return],16,vec![Slot{offset:0,size:16},Slot{offset:4,size:8}],Slot{offset:0,size:16});
    compare(&p,&plan_for(&p),&[u128::MAX,0x0123456789abcdef],1);
}
fn plan_for(p:&Program)->Plan {plan(p)}

#[test]
fn scalar_local_address_bits_and_dead_fallible_operations_survive() {
    let mut p=program(vec![local(0,3),local(1,0),store(1,0,8),Op::Return],8,vec![],Slot{offset:0,size:8});
    for size in [0,64,100] {p.data=vec![0;size];let plan=plan(&p);for budget in 0..=5 {compare(&p,&plan,&[],budget);}}
    for (op,a,b,signed) in [(Binary::Div,5,0,false),(Binary::Rem,1u128<<63,u64::MAX as u128,true),(Binary::Div,6,2,false)] {
        let p=program(vec![Op::Imm{dst:0,value:a},Op::Imm{dst:1,value:b},
            Op::Binary{dst:2,overflow:3,op,a:0,b:1,bits:64,signed},Op::Return],0,vec![],Slot{offset:0,size:0});
        let plan=plan(&p);assert_eq!(summary(&Ok(plan.clone())).live_computations_per_pc[2],1);
        for budget in 0..=5 {compare(&p,&plan,&[],budget);}
    }
    let p=program(vec![local(0,0),load(1,0,8),Op::Assert{value:1,expected:true,message:"retained".into()},
        Op::Trap{message:"also retained".into()}],8,vec![Slot{offset:0,size:8}],Slot{offset:0,size:0});
    let plan=plan(&p);for input in [0,1] {for budget in 0..=5 {compare(&p,&plan,&[input],budget);}}
}

#[test]
fn scalar_integer_widths_output_aliases_and_dynamic_fill_match_bytecode() {
    let operations=[Binary::Add,Binary::Sub,Binary::Mul,Binary::Div,Binary::Rem,Binary::And,Binary::Or,Binary::Xor,
        Binary::Shl,Binary::Shr,Binary::Eq,Binary::Ne,Binary::Lt,Binary::Le,Binary::Gt,Binary::Ge,Binary::Cmp,
        Binary::RotateLeft,Binary::RotateRight];
    for bits in [8,16,32,64,128] {for op in operations {for signed in [false,true] {for alias in [false,true] {
        let p=program(vec![local(0,0),local(1,16),load(2,0,16),load(3,1,16),
            Op::Binary{dst:2,overflow:if alias {2} else {3},op,a:2,b:3,bits,signed},
            local(0,32),store(0,2,16),Op::Return],48,vec![Slot{offset:0,size:16},Slot{offset:16,size:16}],Slot{offset:32,size:16});
        let plan=plan(&p);for args in [[0,0],[u128::MAX,1],[1u128<<127,u128::MAX],[0x123456789abcdef,129]] {
            compare(&p,&plan,&args,8);
        }
    }}}}
    let p=program(vec![local(0,0),local(1,16),Op::Imm{dst:2,value:16},Op::CopyDynamic{dst:1,src:0,size:2},
        Op::Imm{dst:2,value:7},Op::Imm{dst:3,value:0x1234},Op::FillBytes{address:0,value:3,size:2},
        Op::Imm{dst:2,value:0},Op::CopyDynamic{dst:7,src:7,size:2},Op::Return],32,
        vec![Slot{offset:0,size:16}],Slot{offset:0,size:16});
    let plan=plan(&p);compare(&p,&plan,&[u128::MAX],10);
}

#[test]
fn scalar_declines_cycles_unsupported_operations_and_work_exhaustion() {
    let cycle=program(vec![Op::Jump{target:0}],0,vec![],Slot{offset:0,size:0});
    let memory=crate::proof::memory_plan(&cycle,0,&mut crate::proof::MAX_GLOBAL_WORK.clone());assert!(memory.eligible);
    assert_eq!(lower(&cycle.functions[0],&memory,250_000).unwrap_err(),"scalar_cycle");
    let p=program(vec![Op::Return,Op::Jump{target:1}],0,vec![],Slot{offset:0,size:0});
    let plan=plan(&p);assert_eq!(plan.maximum_steps,1);compare(&p,&plan,&[],1);
    let memory=crate::proof::memory_plan(&p,0,&mut crate::proof::MAX_GLOBAL_WORK.clone());
    assert_eq!(lower(&p.functions[0],&memory,0).unwrap_err(),"scalar_work_limit");
    let p=program(vec![Op::FloatBinary{dst:0,op:crate::FloatBinary::Add,a:1,b:2,bits:32},Op::Return],0,vec![],Slot{offset:0,size:0});
    let memory=crate::proof::memory_plan(&p,0,&mut crate::proof::MAX_GLOBAL_WORK.clone());assert!(memory.eligible);
    assert_eq!(lower(&p.functions[0],&memory,250_000).unwrap_err(),"scalar_unsupported");
}
