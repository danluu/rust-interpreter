use super::*;
use crate::{Function,Slot,Op,Engine,VERSION,execute_profiled,Limits,ExecutionProfile};

fn local(dst:Reg,offset:usize)->Op {Op::Local{dst,offset}}
fn load(dst:Reg,address:Reg,size:u8)->Op {Op::Load{dst,address,size}}
fn function(name:&str,frame_size:usize,frame_align:usize,args:Vec<Slot>,result:Slot,code:Vec<Op>)->Function {
    Function{name:name.into(),frame_size,frame_align,registers:8,args,result,code}
}
fn program(functions:Vec<Function>)->Program {Program{version:VERSION,target:"aarch64-apple-darwin".into(),entry:0,functions,data:vec![],statics:vec![],thread_locals:vec![]}}
fn counts(profile:&ExecutionProfile)->Vec<Vec<u64>> {
    profile.functions.iter().map(|f|{
        let mut result=f.interpreted.clone();
        for (n,h) in result.iter_mut().zip(&f.jit_scalar_hits) {*n+=h;}
        for (pc,hits) in f.jit_blocks.iter().enumerate() {if *hits!=0 {for n in &mut result[pc..f.jit_block_ends[pc]] {*n+=hits;}}}
        result
    }).collect()
}
#[derive(Default)]
struct Statistics {commits:usize,declines:usize}
fn compare(p:&Program,args:&[u128],budget:u64,memory:usize,frames:usize)->Statistics {
    let options=||Limits{instructions:budget,memory,frames,..Limits::default()};
    let reference=execute_profiled(p,args,options(),Engine::Interpreter);
    let mut statistics=Statistics::default();
    for persistent in [false,true] {
        let mut limits=options();limits.jit_resumable_calls=true;limits.jit_scalar_calls=true;
        limits.jit_persistent_registers=persistent;
        let mut baseline_limits=limits.clone();baseline_limits.jit_scalar_calls=false;
        let baseline=execute_profiled(p,args,baseline_limits,Engine::Jit);
        let actual=execute_profiled(p,args,limits,Engine::Jit);
        match (&reference,actual) {
            (Ok((a,ap)),Ok((b,bp)))=>{
                assert_eq!((a.value,a.instructions,a.peak_memory),(b.value,b.instructions,b.peak_memory));
                assert_eq!(counts(ap),counts(&bp));
                let scalar:u64=bp.functions.iter().flat_map(|f|&f.jit_scalar_hits).sum();
                let native:u64=bp.functions.iter().map(|f|f.jit_blocks.iter().enumerate().map(|(pc,h)|
                    if *h==0 {0} else {*h*(f.jit_block_ends[pc]-pc) as u64}).sum::<u64>()).sum();
                assert_eq!(b.jit_instructions,scalar+native);
                statistics.commits=bp.functions.iter().zip(&p.functions).map(|(p,f)|p.jit_scalar_hits.iter().zip(&f.code)
                    .filter(|(_,op)|matches!(op,Op::Return)).map(|(hits,_)|*hits as usize).sum::<usize>()).sum();
                let calls:usize=counts(ap).iter().zip(&p.functions).map(|(hits,f)|hits.iter().zip(&f.code)
                    .filter(|(_,op)|matches!(op,Op::Call{..})).map(|(hits,_)|*hits as usize).sum::<usize>()).sum();
                statistics.declines=calls-statistics.commits;
            },
            (Err(a),Err(b))=>{
                // The adopted JIT already uses one Memory fault message for
                // bounds and readonly failures. Require exact baseline-JIT
                // error behavior; interpreter wording differs for that class.
                assert_eq!(baseline.unwrap_err(),b);
                assert!(*a==b || (b=="JIT guest memory access failed"
                    && matches!(a.as_str(),"invalid guest memory access"|"write to read-only guest memory")),"interpreter {a}, JIT {b}");
            },
            (a,b)=>panic!("reference {a:?}, native scalar transaction {b:?}"),
        }
    }
    statistics
}
fn pair()->Program {
    let parent=function("parent",32,8,vec![Slot{offset:0,size:16},Slot{offset:16,size:8}],Slot{offset:0,size:16},vec![
        local(0,0),local(1,16),Op::Call{function:1,args:vec![0,1],destination:0},
        Op::Call{function:1,args:vec![0,1],destination:1},Op::Return]);
    let leaf=function("overlap leaf",32,64,vec![Slot{offset:0,size:16},Slot{offset:4,size:8}],Slot{offset:0,size:16},
        vec![local(0,0),local(1,1),Op::Imm{dst:2,value:7},Op::CopyDynamic{dst:1,src:0,size:2},Op::Return]);
    program(vec![parent,leaf])
}

#[test]
fn native_scalar_call_matches_complete_vm_aliases_profiles_and_peak_memory() {
    let p=pair();
    for args in [[0,0],[u128::MAX,0x0123456789abcdef],[0x0123456789abcdef_fedcba9876543210,0x8877665544332211]] {
        let stats=compare(&p,&args,100,4096,8);assert_eq!(stats.commits,2);assert_eq!(stats.declines,0);
    }
    let run=crate::execute_with_engine(&p,&[u128::MAX,7],Limits{jit_resumable_calls:true,jit_scalar_calls:true,..Limits::default()},Engine::Jit).unwrap();
    assert_eq!(run.jit_resumable_calls,2);

}

#[test]
fn native_scalar_call_resource_tails_and_original_error_order_match() {
    let p=pair();for budget in 0..=17 {for memory in [0,15,31,64,127,128,191,255,256,511,512,4096] {for frames in 0..=3 {
        compare(&p,&[123,7],budget,memory,frames);
    }}}
    let parent=function("parent",16,8,vec![Slot{offset:0,size:8}],Slot{offset:8,size:8},vec![
        local(0,0),Op::Imm{dst:1,value:8},Op::Call{function:1,args:vec![0],destination:1},Op::Return]);
    let leaf=function("fault before readonly return",8,8,vec![Slot{offset:0,size:8}],Slot{offset:0,size:8},vec![
        local(0,0),load(1,0,8),Op::Assert{value:1,expected:true,message:"check first".into()},Op::Return]);
    let mut p=program(vec![parent,leaf]);p.data=vec![0;64];
    for arg in [0,1] {for budget in 0..=10 {compare(&p,&[arg],budget,4096,8);}}
    p.functions[1].code[2]=Op::Trap{message:"trap first".into()};compare(&p,&[1],100,4096,8);
}

#[test]
fn native_scalar_call_new_frame_arguments_and_result_padding_fall_back() {
    let parent=function("new frame aliases",17,8,vec![Slot{offset:0,size:8}],Slot{offset:8,size:8},vec![
        local(0,0),Op::Imm{dst:1,value:64},local(2,8),Op::Call{function:1,args:vec![0,1],destination:2},Op::Return]);
    let leaf=function("ordered arguments",16,64,vec![Slot{offset:0,size:8},Slot{offset:8,size:8}],Slot{offset:8,size:8},vec![Op::Return]);
    let mut p=program(vec![parent,leaf]);let stats=compare(&p,&[0xabcdef],100,4096,8);assert_eq!(stats.commits,0);assert_eq!(stats.declines,1);
    // Destination in newly published padding is valid only after ordinary
    // frame reservation. The caller observes it after the leaf returns.
    p.functions[0].code=vec![local(0,0),Op::Imm{dst:1,value:40},
        Op::Call{function:1,args:vec![0,0],destination:1},load(2,1,8),local(3,8),Op::Store{address:3,src:2,size:8},Op::Return];
    let stats=compare(&p,&[0x123456],100,4096,8);assert_eq!(stats.commits,0);assert_eq!(stats.declines,1);
    p.functions[0].code[1]=Op::Imm{dst:1,value:64};
    // This result lies in the callee payload and is invalid again on return.
    let stats=compare(&p,&[0x123456],100,4096,8);assert_eq!(stats.commits,0);
}

#[test]
fn native_scalar_call_preserves_escaped_addresses_and_future_zeroing() {
    let parent=function("parent",17,8,vec![],Slot{offset:8,size:8},vec![local(0,0),local(1,8),
        Op::Call{function:1,args:vec![],destination:0},load(2,0,8),
        Op::Call{function:2,args:vec![2],destination:1},Op::Return]);
    let escaping=function("logical address",8,64,vec![],Slot{offset:0,size:8},vec![local(0,0),Op::Store{address:0,src:0,size:8},Op::Return]);
    let identity=function("future payload",8,8,vec![Slot{offset:0,size:8}],Slot{offset:0,size:8},vec![Op::Return]);
    let p=program(vec![parent,escaping,identity]);let stats=compare(&p,&[],100,4096,8);assert_eq!(stats.commits,1);assert_eq!(stats.declines,1);
    for budget in 0..=12 {compare(&p,&[],budget,4096,8);}
}


#[test]
fn native_scalar_call_private_failures_and_full_width_switches_replay_original_errors() {
    let mut p=pair();
    p.functions[1].code=vec![local(0,0),load(1,0,16),
        Op::Assert{value:1,expected:true,message:"scalar private assertion".into()},Op::Return];
    for arg in [0,1,1u128<<100,u128::MAX] {for budget in 0..25 {compare(&p,&[arg,0],budget,4096,8);}}
    p.functions[1].code[2]=Op::Trap{message:"scalar private trap".into()};
    compare(&p,&[1,0],100,4096,8);
    p.functions[1].code=vec![local(0,0),load(1,0,8),Op::Imm{dst:2,value:0},
        Op::Binary{dst:3,overflow:4,op:crate::Binary::Div,a:1,b:2,bits:64,signed:false},Op::Return];
    for budget in 0..25 {compare(&p,&[123,0],budget,4096,8);}
    p.functions[1].code=vec![local(0,0),load(1,0,16),
        Op::Switch{value:1,cases:vec![(1u128<<100,4)],otherwise:3},Op::Return,Op::Return];
    for arg in [0,1,1u128<<100] {compare(&p,&[arg,0],100,4096,8);}
}

#[test]
fn native_scalar_call_heap_pointer_boundaries_and_large_caller_registers_match() {
    let parent=function("pointer source",16,8,vec![Slot{offset:0,size:8}],Slot{offset:8,size:8},vec![
        local(0,0),load(1,0,8),local(2,8),Op::Call{function:1,args:vec![1],destination:2},Op::Return]);
    let leaf=function("heap copied scalar",8,8,vec![Slot{offset:0,size:8}],Slot{offset:0,size:8},vec![Op::Return]);
    let mut p=program(vec![parent,leaf]);p.statics=vec![0x5a;64];
    let tag=crate::heap::TAG as u128;
    for address in [0,1,16,24,32,tag-1,tag,tag+1,tag+16,tag+55,tag+56,tag+57,tag+64,u64::MAX as u128] {
        compare(&p,&[address],100,65536,8);
    }
    p.functions[0].registers=4096;
    p.functions[0].code=vec![local(4095,0),load(4094,4095,8),local(4093,8),
        Op::Call{function:1,args:vec![4094],destination:4093},Op::Return];
    compare(&p,&[tag+16],100,1<<20,8);
    p.functions[0].code[3]=Op::Call{function:1,args:vec![4093],destination:4094};
    for address in [0,tag,tag+16,tag+56,tag+57,u64::MAX as u128] {compare(&p,&[address],100,1<<20,8);}
}

#[test]
fn native_scalar_call_shared_arena_maps_and_prepared_option_identity_are_exact() {
    let p=pair();
    for profiled in [false,true] {
        let mut jit=Jit::new_resumable(&p,profiled,16*1024*1024,true).unwrap();jit.enable_scalar_calls();
        jit.ensure_function(0).unwrap();
        let entry=jit.scalar_entry(1).unwrap();assert_eq!(entry.offset,0);
        assert!(entry.bytes>0 && entry.bytes<jit.bytes);
        jit.ensure_function(1).unwrap();
        let before=jit.bytes;assert!(!jit.ensure_function(0).unwrap());assert_eq!(jit.bytes,before);
        let map=serde_json::to_value(jit.operation_map().unwrap()).unwrap();
        assert_eq!(map["schema_version"],2);assert_eq!(map["code_bytes"],jit.bytes);
        let mut end=0;
        for f in map["functions"].as_array().unwrap() {
            assert_eq!(f["offset"].as_u64().unwrap() as usize,end);
            for s in f["spans"].as_array().unwrap() {
                assert_eq!(s["offset"].as_u64().unwrap() as usize,end);
                end=s["end"].as_u64().unwrap() as usize;
            }
            assert_eq!(f["end"].as_u64().unwrap() as usize,end);
        }
        assert_eq!(end,jit.bytes);
    }
    for capacity in [0,4,64,256,1024] {
        let limits=Limits{jit_code_bytes:capacity,jit_resumable_calls:true,jit_scalar_calls:true,..Limits::default()};
        let native=crate::execute_with_engine(&p,&[123,7],limits,Engine::Jit).unwrap();
        let plain=crate::execute(&p,&[123,7],Limits::default()).unwrap();
        assert_eq!((native.value,native.instructions,native.peak_memory),(plain.value,plain.instructions,plain.peak_memory));
        assert!(native.jit_bytes<=capacity);
    }
    let limits=Limits{jit_resumable_calls:true,jit_scalar_calls:true,..Limits::default()};
    let mut prepared=crate::PreparedJit::new(&p,&limits).unwrap();
    for arg in [0,123,u128::MAX,1<<90] {
        let a=prepared.execute(&[arg,7],limits.clone()).unwrap();let b=crate::execute(&p,&[arg,7],Limits::default()).unwrap();
        assert_eq!((a.value,a.instructions,a.peak_memory),(b.value,b.instructions,b.peak_memory));
    }
    let mut changed=limits.clone();changed.jit_scalar_calls=false;
    assert!(prepared.execute(&[1,7],changed).unwrap_err().contains("options changed"));
    let mut partial=p.clone();partial.version|=crate::PARTIAL_VALIDATION;
    assert!(crate::PreparedJit::new(&partial,&limits).err().unwrap().contains("full validation"));
    let bad=Limits{jit_scalar_calls:true,..Limits::default()};
    assert!(crate::execute_with_engine(&p,&[1,7],bad,Engine::Jit).unwrap_err().contains("resumable"));
}
