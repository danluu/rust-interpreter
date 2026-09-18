use super::*;
use crate::{Function,Slot,Op,Engine,VERSION,execute_profiled};

fn local(dst:Reg,offset:usize)->Op {Op::Local{dst,offset}}
fn load(dst:Reg,address:Reg,size:u8)->Op {Op::Load{dst,address,size}}
fn function(name:&str,frame_size:usize,frame_align:usize,args:Vec<Slot>,result:Slot,code:Vec<Op>)->Function {
    Function{name:name.into(),frame_size,frame_align,registers:8,args,result,code}
}
fn program(functions:Vec<Function>)->Program {Program{version:VERSION,target:"aarch64-apple-darwin".into(),entry:0,functions,data:vec![],statics:vec![],thread_locals:vec![]}}
fn counts(profile:&ExecutionProfile)->Vec<Vec<u64>> {
    profile.functions.iter().map(|f|{
        let mut result=f.interpreted.clone();
        for (pc,hits) in f.jit_blocks.iter().enumerate() {if *hits!=0 {for n in &mut result[pc..f.jit_block_ends[pc]] {*n+=hits;}}}
        result
    }).collect()
}
fn compare(p:&Program,args:&[u128],budget:u64,memory:usize,frames:usize)->Statistics {
    let options=||Limits{instructions:budget,memory,frames,..Limits::default()};
    let reference=execute_profiled(p,args,options(),Engine::Interpreter);
    let guard=Enabled::new();let actual=execute_profiled(p,args,options(),Engine::Interpreter);
    let statistics=STATISTICS.with(Cell::get);drop(guard);
    match (reference,actual) {
        (Ok((a,ap)),Ok((b,bp)))=>{
            assert_eq!((a.value,a.instructions,a.peak_memory),(b.value,b.instructions,b.peak_memory));
            assert_eq!(counts(&ap),counts(&bp));assert_eq!(b.jit_entries as usize,statistics.commits);
            assert_eq!(b.jit_resumable_calls as usize,statistics.commits);assert_eq!(b.jit_resumable_returns as usize,statistics.commits);
            assert_eq!(b.jit_instructions>0,statistics.commits>0);
        },
        (Err(a),Err(b))=>assert_eq!(a,b),
        (a,b)=>panic!("reference {a:?}, scalar transaction {b:?}"),
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
fn scalar_call_transaction_matches_complete_vm_aliases_profiles_and_peak_memory() {
    let p=pair();
    for args in [[0,0],[u128::MAX,0x0123456789abcdef],[0x0123456789abcdef_fedcba9876543210,0x8877665544332211]] {
        let stats=compare(&p,&args,100,4096,8);assert_eq!(stats.commits,2);assert_eq!(stats.declines,0);
    }
    let guard=Enabled::new();let run=crate::execute(&p,&[u128::MAX,7],Limits::default()).unwrap();
    assert_eq!(STATISTICS.with(Cell::get).commits,2);assert_eq!(run.jit_resumable_calls,2);drop(guard);
}

#[test]
fn scalar_call_transaction_resource_tails_and_original_error_order_match() {
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
fn scalar_call_transaction_new_frame_arguments_and_result_padding_fall_back() {
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
    let stats=compare(&p,&[0x123456],100,4096,8);assert_eq!(stats.commits,0);assert_eq!(stats.declines,1);
}

#[test]
fn scalar_call_transaction_preserves_escaped_addresses_and_future_zeroing() {
    let parent=function("parent",17,8,vec![],Slot{offset:8,size:8},vec![local(0,0),local(1,8),
        Op::Call{function:1,args:vec![],destination:0},load(2,0,8),
        Op::Call{function:2,args:vec![2],destination:1},Op::Return]);
    let escaping=function("logical address",8,64,vec![],Slot{offset:0,size:8},vec![local(0,0),Op::Store{address:0,src:0,size:8},Op::Return]);
    let identity=function("future payload",8,8,vec![Slot{offset:0,size:8}],Slot{offset:0,size:8},vec![Op::Return]);
    let p=program(vec![parent,escaping,identity]);let stats=compare(&p,&[],100,4096,8);assert_eq!(stats.commits,1);assert_eq!(stats.declines,1);
    for budget in 0..=12 {compare(&p,&[],budget,4096,8);}
}

#[derive(Debug,PartialEq,Eq)]
struct Snapshot {bytes:Vec<u8>,heap:Vec<u8>,peak:usize,limit:usize,readonly:usize,auxiliary:usize}
fn snapshot(m:&Memory)->Snapshot {Snapshot{bytes:m.bytes.to_vec(),heap:m.heap.bytes.to_vec(),peak:m.peak,limit:m.limit,readonly:m.readonly_end,auxiliary:m.auxiliary_bytes}}
fn memory()->Memory {Memory{bytes:vec![0x57;33].into(),heap:crate::heap::Heap::default(),limit:4096,readonly_end:16,peak:33,auxiliary_bytes:0}}

#[test]
fn scalar_call_transaction_declines_leave_all_guest_visible_memory_unchanged() {
    let leaf=function("private failure",8,64,vec![Slot{offset:0,size:8}],Slot{offset:0,size:8},vec![local(0,0),load(1,0,8),
        Op::Assert{value:1,expected:false,message:"discard private work".into()},Op::Return]);let p=program(vec![leaf]);
    let guard=Enabled::new();let mut context=Context::new(&p,false,false).unwrap().unwrap();
    for (source,destination,budget,frames,working) in [(16,24,100,1,4096),(64,24,100,1,4096),(16,8,100,1,4096),
        (usize::MAX,24,100,1,4096),(16,24,0,1,4096),(16,24,100,8,4096),(16,24,100,1,64)] {
        let mut memory=memory();let before=snapshot(&memory);
        let options=Limits{memory:working,frames:8,..Limits::default()};
        let result=context.try_call(0,&[0],&[source as u128],destination,&mut memory,128,frames,&options,budget,None).unwrap();
        assert!(result.is_none());assert_eq!(snapshot(&memory),before);
    }
    let mut quota=Context::new(&p,false,false).unwrap().unwrap();quota.mappings=64;
    let mut m=memory();let before=snapshot(&m);assert!(quota.try_call(0,&[0],&[16],24,&mut m,128,1,&Limits::default(),100,None).unwrap().is_none());
    assert_eq!(snapshot(&m),before);assert_eq!(quota.mappings,64);
    let mut profiled=Context::new(&p,true,false).unwrap().unwrap();assert!(profiled.try_call(0,&[0],&[16],24,&mut m,128,1,&Limits::default(),100,None).is_err());
    assert_eq!(snapshot(&m),before);drop(guard);
}

#[test]
fn scalar_call_transaction_indirect_signatures_and_strict_mode_are_explicit() {
    let parent=function("indirect parent",16,8,vec![Slot{offset:0,size:8}],Slot{offset:8,size:8},vec![
        local(0,0),local(1,8),Op::Imm{dst:2,value:(crate::FUNCTION_POINTER_TAG|2) as u128},
        Op::CallIndirect{callee:2,args:vec![0],destination:1,arg_sizes:vec![8],result_size:8},Op::Return]);
    let leaf=function("identity",8,8,vec![Slot{offset:0,size:8}],Slot{offset:0,size:8},vec![Op::Return]);let mut p=program(vec![parent,leaf]);
    let stats=compare(&p,&[123],100,4096,8);assert_eq!(stats.commits,1);
    p.functions[0].code[3]=Op::CallIndirect{callee:2,args:vec![0],destination:1,arg_sizes:vec![16],result_size:8};
    compare(&p,&[123],100,4096,8);
    p.functions[0].code[2]=Op::Imm{dst:2,value:0};compare(&p,&[123],100,4096,8);
    let guard=Enabled::new();assert!(Context::new(&p,false,true).is_err());p.version|=PARTIAL_VALIDATION;
    assert!(Context::new(&p,false,false).is_err());drop(guard);
}
