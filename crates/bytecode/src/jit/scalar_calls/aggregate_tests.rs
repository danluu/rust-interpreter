//! Complete Call/Return comparisons, including memory on every error exit.
use super::*;
use crate::scalar_call_model::with_memory_snapshot;

struct Observation {
    result:Result<(u128,u64,usize),String>,
    memory:Option<(Vec<u8>,Vec<u8>)>,
    counts:Option<Vec<Vec<u64>>>,
    commits:usize,
}
fn observe(p:&Program,args:&[u128],limits:Limits,engine:Engine,profiled:bool)->Observation {
    let ((result,profile),memory)=with_memory_snapshot(|| {
        if profiled {match execute_profiled(p,args,limits,engine) {
            Ok((execution,profile))=>(Ok(execution),Some(profile)),Err(e)=>(Err(e),None),
        }} else {(crate::execute_with_engine(p,args,limits,engine),None)}
    });
    let commits=profile.as_ref().map_or(0,|profile|profile.functions.iter().zip(&p.functions).map(|(row,f)|
        row.jit_scalar_hits.iter().zip(&f.code).filter(|(_,op)|matches!(op,Op::Return)).map(|(h,_)|*h as usize).sum::<usize>()).sum());
    if let (Ok(run),Some(profile))=(&result,&profile) {
        let native=profile.functions.iter().map(|row|row.jit_scalar_hits.iter().sum::<u64>()+
            row.jit_blocks.iter().enumerate().map(|(pc,h)|if *h==0 {0} else {*h*(row.jit_block_ends[pc]-pc) as u64}).sum::<u64>()).sum::<u64>();
        assert_eq!(run.jit_instructions,native);
    }
    Observation{result:result.map(|r|(r.value,r.instructions,r.peak_memory)),memory,
        counts:profile.as_ref().map(counts),commits}
}
fn compare_complete(p:&Program,args:&[u128],limits:Limits)->usize {
    let mut commits=0;
    for profiled in [false,true] {
        let reference=observe(p,args,limits.clone(),Engine::Interpreter,profiled);
        for persistent in [false,true] {
            let mut options=limits.clone();options.jit_resumable_calls=true;options.jit_persistent_registers=persistent;
            let baseline=observe(p,args,options.clone(),Engine::Jit,profiled);
            options.jit_scalar_calls=true;
            let actual=observe(p,args,options,Engine::Jit,profiled);
            assert_eq!(actual.result,baseline.result,"baseline JIT result/error");
            assert_eq!(actual.memory,baseline.memory,"baseline JIT full error/success memory");
            assert_eq!(actual.counts,baseline.counts);
            assert_eq!(actual.memory,reference.memory,"ordinary interpreter full error/success memory");
            match (&reference.result,&actual.result) {
                (Ok(a),Ok(b))=>{assert_eq!(a,b);assert_eq!(reference.counts,actual.counts);},
                (Err(a),Err(b))=>assert!(a==b || (b=="JIT guest memory access failed"
                    && matches!(a.as_str(),"invalid guest memory access"|"write to read-only guest memory")),"interpreter {a}, JIT {b}"),
                (a,b)=>panic!("interpreter {a:?}, native aggregate {b:?}"),
            }
            if profiled {commits=actual.commits;}
        }
    }
    commits
}
fn limits()->Limits {Limits{instructions:2048,memory:65536,frames:8,..Limits::default()}}
fn pair(width:usize)->Program {
    let parent=function("aggregate parent",137,8,(0..3).map(|i|Slot{offset:i*16,size:16}).collect(),Slot{offset:0,size:16},vec![
        local(0,0),local(1,16),local(2,32),local(3,1),Op::Call{function:1,args:vec![0,1,2],destination:3},
        Op::Call{function:1,args:vec![0,1,2],destination:3},Op::Return]);
    let leaf=function("aggregate alias leaf",1024,64,vec![Slot{offset:0,size:16},Slot{offset:8,size:8},Slot{offset:32,size:16}],
        Slot{offset:0,size:width},vec![local(0,0),local(1,17),Op::Copy{src:0,dst:1,size:31},Op::Return]);
    program(vec![parent,leaf])
}

#[test]
fn every_return_width_commits_full_aliases_and_retained_padding() {
    let args=[u128::MAX,0x0123456789abcdef_fedcba9876543210,0x0102030405060708_090a0b0c0d0e0f00];
    for width in 0..=64 {
        let mut p=pair(width);assert_eq!(compare_complete(&p,&args,limits()),2,"width {width}");
        if width>16 {p.functions[1].frame_size=512;assert_eq!(compare_complete(&p,&args,limits()),2);}
    }
}

#[test]
fn aggregate_heap_linear_readonly_and_overflow_boundaries_match() {
    let parent=function("aggregate address inputs",32,8,vec![Slot{offset:0,size:8},Slot{offset:8,size:8}],Slot{offset:16,size:8},vec![
        local(0,0),load(1,0,8),local(2,8),load(3,2,8),Op::Call{function:1,args:vec![1],destination:3},Op::Return]);
    let leaf=function("wide copied input",64,64,vec![Slot{offset:0,size:16}],Slot{offset:0,size:63},vec![Op::Return]);
    let mut p=program(vec![parent,leaf]);p.data=vec![0x5a;64];p.statics=vec![0x6b;128];
    let tag=crate::heap::TAG as u128;
    for source in [0,1,48,49,64,80,81,95,96,127,128,tag,tag+112,tag+113,u64::MAX as u128] {
        compare_complete(&p,&[source,tag+32],limits());
    }
    for destination in [0,1,63,64,65,80,81,96,127,128,tag-1,tag,tag+65,tag+66,tag+128,u64::MAX as u128] {
        compare_complete(&p,&[tag,destination],limits());
    }
    assert_eq!(compare_complete(&p,&[tag,tag+65],limits()),1);
}

#[test]
fn aggregate_resource_and_instruction_tails_preserve_complete_memory() {
    let p=pair(40);let args=[0x123456789abcdef,u128::MAX,1<<100];
    for instructions in 0..=17 {for memory in [0,15,153,255,447,1215,1216,1471,1472,65536] {for frames in [0,1,2,3] {
        compare_complete(&p,&args,Limits{instructions,memory,frames,..Limits::default()});
    }}}
}

#[test]
fn aggregate_private_faults_replay_before_readonly_return_and_preserve_writes() {
    let mut p=pair(64);p.data=vec![0x55;64];
    for error in [Op::Assert{value:1,expected:false,message:"late aggregate assertion".into()},
        Op::Binary{dst:2,overflow:3,op:crate::Binary::Div,a:1,b:4,bits:64,signed:false},
        Op::Trap{message:"late aggregate trap".into()}] {
        p.functions[1].code=vec![local(0,0),load(1,0,16),local(2,48),Op::Store{address:2,src:1,size:16},
            Op::Imm{dst:4,value:0},error,Op::Return];
        for readonly in [false,true] {
            p.functions[0].code[3]=if readonly {Op::Imm{dst:3,value:8}} else {local(3,1)};
            for input in [0,1,1u128<<100] {for instructions in 0..=20 {
                compare_complete(&p,&[input,u128::MAX,7],Limits{instructions,..limits()});
            }}
        }
    }
}

#[test]
fn aggregate_new_frame_input_and_new_padding_destination_replay_in_order() {
    let parent=function("aggregate fresh aliases",65,8,vec![Slot{offset:0,size:16}],Slot{offset:16,size:16},vec![
        local(0,0),Op::Imm{dst:1,value:256},local(2,16),Op::Call{function:1,args:vec![0,1],destination:2},Op::Return]);
    let leaf=function("fresh ordered capture",64,256,vec![Slot{offset:0,size:16},Slot{offset:8,size:16}],Slot{offset:0,size:40},vec![Op::Return]);
    let mut p=program(vec![parent,leaf]);
    assert_eq!(compare_complete(&p,&[0xabcdef1234567890_0102030405060708],limits()),0);
    p.functions[0].code=vec![local(0,0),Op::Imm{dst:2,value:96},Op::Call{function:1,args:vec![0,0],destination:2},
        load(3,2,16),local(4,16),Op::Store{address:4,src:3,size:16},Op::Return];
    assert_eq!(compare_complete(&p,&[u128::MAX],limits()),0);
    for destination in [80,81,95,96,216,217,255,256,280,319,320] {
        p.functions[0].code[1]=Op::Imm{dst:2,value:destination};
        compare_complete(&p,&[u128::MAX],limits());
    }
}

#[test]
fn aggregate_escaped_pointer_future_zeroing_and_zero_result_destinations_match() {
    let parent=function("wide escaped pointer",80,8,vec![],Slot{offset:64,size:16},vec![local(0,0),
        Op::Call{function:1,args:vec![],destination:0},local(1,24),load(2,1,8),local(3,64),
        Op::Call{function:2,args:vec![2],destination:3},Op::Return]);
    let leaf=function("wide pointer bits",64,256,vec![],Slot{offset:0,size:64},vec![local(0,0),local(1,24),Op::Store{address:1,src:0,size:8},Op::Return]);
    let identity=function("future zero bytes",64,8,vec![Slot{offset:0,size:16}],Slot{offset:0,size:16},vec![Op::Return]);
    let p=program(vec![parent,leaf,identity]);assert_eq!(compare_complete(&p,&[],limits()),1);
    for instructions in 0..=15 {compare_complete(&p,&[],Limits{instructions,..limits()});}
    let mut p=pair(0);p.functions[0].code[3]=Op::Imm{dst:3,value:u64::MAX as u128};
    assert_eq!(compare_complete(&p,&[1,2,3],limits()),2);
}

#[test]
fn aggregate_selection_bounds_shared_arena_and_global_work_are_explicit() {
    let p=pair(40);
    for profiled in [false,true] {
        let mut jit=Jit::new_resumable(&p,profiled,16*1024*1024,true).unwrap();jit.enable_scalar_calls();
        jit.ensure_function(0).unwrap();let entry=jit.scalar_entry(1).unwrap();
        let words=jit.reconstruct_scalar(1).unwrap();assert_eq!(words.len()*4,entry.bytes);
        assert!(!jit.ensure_function(0).unwrap());assert!(jit.operation_map().is_ok());
    }
    for proof_empty in [false,true] {
        let mut jit=Jit::new_resumable(&p,false,16*1024*1024,true).unwrap();jit.enable_scalar_calls();
        if proof_empty {jit.scalar.as_mut().unwrap().proof_work=0;} else {jit.scalar.as_mut().unwrap().scalar_work=0;}
        jit.ensure_function(0).unwrap();assert!(jit.scalar_entry(1).is_none());
    }
    let mut proof_work=proof::MAX_GLOBAL_WORK;let mut scalar_work=1_000_000;
    assert!(call_plan(&p,1,&mut proof_work,&mut scalar_work).is_ok());assert_eq!(scalar_work,0);
    for (frame,size,expected) in [(512,3,false),(512,16,true),(512,40,true),(1024,3,true),(1025,40,false),(1024,65,false)] {
        let mut p=pair(size);p.functions[1].frame_size=frame;p.functions[1].code=vec![Op::Return];
        let mut jit=Jit::new_resumable(&p,false,16*1024*1024,true).unwrap();jit.enable_scalar_calls();
        jit.ensure_function(0).unwrap();assert_eq!(jit.scalar_entry(1).is_some(),expected,"frame {frame}, result {size}");
    }
    // Legacy uninitialized small results do not gain the new zeroed policy.
    let mut p=pair(16);p.functions[1].frame_size=512;p.functions[1].args.clear();p.functions[1].code=vec![Op::Return];
    for op in &mut p.functions[0].code {if let Op::Call{args,..}=op {args.clear();}}
    let mut jit=Jit::new_resumable(&p,false,16*1024*1024,true).unwrap();jit.enable_scalar_calls();
    jit.ensure_function(0).unwrap();assert!(jit.scalar_entry(1).is_none());
    for capacity in [0,4,64,256,1024] {
        compare_complete(&pair(40),&[1,2,3],Limits{jit_code_bytes:capacity,..limits()});
    }
}
