#![cfg(all(target_arch="aarch64",target_os="macos"))]
use rust_interp_bytecode::{Engine,Execution,Function,Limits,Op,PreparedJit,Program,Slot,VERSION,
    FUNCTION_POINTER_TAG,execute_with_engine,execute_profiled};
#[path="common/call_copy_cases.rs"]
mod cases;

fn options(persistent:bool) -> Limits {
    Limits {jit_resumable_calls:true,jit_indirect_calls:true,jit_persistent_registers:persistent,..Limits::default()}
}
fn compare(want: &Result<Execution,String>, got: Result<Execution,String>) {
    match (want,got) {
        (Ok(a),Ok(b))=>assert_eq!((a.value,a.instructions,a.peak_memory),(b.value,b.instructions,b.peak_memory)),
        (Err(a),Err(b)) if b=="JIT guest memory access failed"=>
            assert!(a.contains("memory access")||a.contains("read-only")||a.contains("address overflow"),"{a}"),
        (Err(a),Err(b))=>assert_eq!(a,&b),
        (a,b)=>panic!("different outcomes: {a:?} / {b:?}"),
    }
}
fn same(p:&Program,args:&[u128],limits:Limits) {
    let plain=Limits {jit_resumable_calls:false,jit_indirect_calls:false,jit_persistent_registers:false,..limits.clone()};
    let want=execute_with_engine(p,args,plain.clone(),Engine::Interpreter);
    for persistent in [false,true] {
        let l=Limits {jit_resumable_calls:true,jit_indirect_calls:true,jit_persistent_registers:persistent,..limits.clone()};
        compare(&want,execute_with_engine(p,args,l.clone(),Engine::Jit));
        let got=execute_profiled(p,args,l,Engine::Jit).map(|(run,profile)| {
            let (_,reference)=execute_profiled(p,args,plain.clone(),Engine::Interpreter).unwrap();
            for (row,old) in profile.functions.iter().zip(&reference.functions) {
                let mut counts=row.interpreted.clone();
                for (pc,&n) in row.jit_blocks.iter().enumerate().filter(|(_,n)|**n!=0) {
                    for count in &mut counts[pc..row.jit_block_ends[pc]] {*count+=n;}
                }
                assert_eq!(counts,old.interpreted);
            }
            run
        });
        compare(&want,got);
    }
}
fn fixture(registers:usize) -> Program {
    let r=(registers-4) as u32;
    Program {version:VERSION,target:"aarch64-apple-darwin".into(),entry:0,data:vec![0;16],statics:vec![],thread_locals:vec![],
        functions:vec![Function {name:"one dynamic call site".into(),frame_size:64,frame_align:16,registers,
            args:vec![Slot{offset:32,size:16}],result:Slot{offset:0,size:8},code:vec![
                Op::Local{dst:r,offset:16},Op::Imm{dst:r+1,value:43},Op::Store{address:r,src:r+1,size:8},
                Op::Local{dst:r+1,offset:32},Op::Load{dst:r+2,address:r+1,size:16},Op::Local{dst:r+3,offset:0},
                Op::CallIndirect{callee:r+2,args:vec![r],arg_sizes:vec![8],destination:r+3,result_size:8},Op::Return]},
            Function {name:"first layout".into(),frame_size:24,frame_align:8,registers:0,args:vec![Slot{offset:8,size:8}],
                result:Slot{offset:8,size:8},code:vec![Op::Return]},
            Function {name:"second layout".into(),frame_size:97,frame_align:128,registers:3000,args:vec![Slot{offset:56,size:8}],
                result:Slot{offset:56,size:8},code:vec![Op::Return]},
            Function {name:"zero initialized registers".into(),frame_size:80,frame_align:32,registers:3001,args:vec![Slot{offset:32,size:8}],
                result:Slot{offset:40,size:8},code:vec![Op::Local{dst:0,offset:40},Op::Store{address:0,src:3000,size:8},Op::Return]}]}
}
fn pointer(id:usize)->u128 {(FUNCTION_POINTER_TAG|(id as u64+1)) as u128}

#[test]
fn native_indirect_multiple_targets_layouts_and_large_registers() {
    for registers in [4,2048,2049,3005] {for persistent in [false,true] {
        let p=fixture(registers);let l=options(persistent);let mut prepared=PreparedJit::new(&p,&l).unwrap();
        for id in [1,2,3,1,2,3] {
            let want=execute_with_engine(&p,&[pointer(id)],Limits::default(),Engine::Interpreter);
            let run=prepared.execute(&[pointer(id)],l.clone()).unwrap();
            assert_eq!(run.value,if id==3 {0}else{43});compare(&want,Ok(run));
        }
        let run=prepared.execute(&[pointer(1)],l).unwrap();assert_eq!(run.jit_resumable_calls,1);
    }}
}

#[test]
fn native_indirect_full_handles_and_signatures_reject_after_warming() {
    let mut p=fixture(4);p.functions.push(Function {name:"wrong signature".into(),args:vec![],..p.functions[1].clone()});
    for persistent in [false,true] {
        let l=options(persistent);let mut prepared=PreparedJit::new(&p,&l).unwrap();
        prepared.execute(&[pointer(1)],l.clone()).unwrap();
        for value in [0,1,FUNCTION_POINTER_TAG as u128,u64::MAX as u128,pointer(99),pointer(4),
            (1u128<<64)|pointer(1),u128::MAX] {
            let want=execute_with_engine(&p,&[value],Limits::default(),Engine::Interpreter);
            assert!(want.is_err());compare(&want,prepared.execute(&[value],l.clone()));
            same(&p,&[value],Limits::default());
        }
        let run=prepared.execute(&[pointer(1)],l).unwrap();assert_eq!(run.value,43);assert_eq!(run.jit_resumable_calls,1);
    }
    let mut wrong_result=fixture(4);wrong_result.functions[1].result.size=4;
    same(&wrong_result,&[pointer(1)],Limits::default());
    let mut wrong_argument=fixture(4);wrong_argument.functions[1].args[0].size=4;
    same(&wrong_argument,&[pointer(1)],Limits::default());
}

#[test]
fn native_indirect_budget_memory_depth_and_code_capacity_boundaries() {
    let p=fixture(4);
    let total=execute_with_engine(&p,&[pointer(1)],Limits::default(),Engine::Interpreter).unwrap().instructions;
    for instructions in 0..=total+1 {same(&p,&[pointer(1)],Limits{instructions,..Limits::default()});}
    for frames in 0..=3 {for memory in [0,16,64,128,175,176,200,255,256,4096] {
        same(&p,&[pointer(1)],Limits{memory,frames,..Limits::default()});
    }}
    for capacity in [0,4,128,1024,4096] {
        same(&p,&[pointer(1)],Limits{jit_code_bytes:capacity,..Limits::default()});
    }
}

fn indirectize(p:&Program)->Program {
    let mut out=p.clone();
    for f in &mut out.functions {
        let pointer_register=f.registers as u32;f.registers+=1;
        let mut positions=Vec::new();let mut next=0;
        for op in &f.code {positions.push(next);next+=if matches!(op,Op::Call{..}) {2}else{1};}
        let mut code=Vec::new();
        for op in &f.code {
            match op {
                Op::Call{function,args,destination}=> {
                    let target=&p.functions[*function];code.push(Op::Imm{dst:pointer_register,value:pointer(*function)});
                    code.push(Op::CallIndirect{callee:pointer_register,args:args.clone(),arg_sizes:target.args.iter().map(|s|s.size).collect(),
                        destination:*destination,result_size:target.result.size});
                },
                Op::Jump{target}=>code.push(Op::Jump{target:positions[*target]}),
                Op::Switch{value,cases,otherwise}=>code.push(Op::Switch{value:*value,
                    cases:cases.iter().map(|(v,t)|(*v,positions[*t])).collect(),otherwise:positions[*otherwise]}),
                _=>code.push(op.clone()),
            }
        }
        f.code=code;
    }
    out
}

#[test]
fn native_indirect_ordered_aliasing_empty_and_faulting_argument_copies() {
    for case in cases::cases() {
        let p=indirectize(&case.program);let want=execute_with_engine(&p,&[],Limits::default(),Engine::Interpreter);
        assert_eq!(want.as_ref().map(|r|r.value).map_err(String::as_str),case.expected,"{}",case.name);
        for frames in [1,2,3] {same(&p,&[],Limits{frames,..Limits::default()});}
        for persistent in [false,true] {
            let l=options(persistent);let mut prepared=PreparedJit::new(&p,&l).unwrap();
            compare(&want,prepared.execute(&[],l.clone()));compare(&want,prepared.execute(&[],l));
        }
    }
}

#[test]
fn native_indirect_arbitrary_copy_widths_and_empty_frames() {
    for size in [0,1,3,8,16,17,31,64,257] {
        let mut p=fixture(4);p.functions.truncate(2);p.functions[0].args.clear();p.functions[0].frame_size=512;
        p.functions[0].result.size=size.min(16);p.data.extend(vec![0x35;size]);
        p.functions[0].code=vec![Op::Imm{dst:0,value:if size==0 {u128::MAX}else{16}},
            Op::Imm{dst:1,value:pointer(1)},Op::Local{dst:2,offset:0},
            Op::CallIndirect{callee:1,args:vec![0],arg_sizes:vec![size],destination:2,result_size:size},Op::Return];
        p.functions[1].frame_size=if size==0 {0}else{size+32};p.functions[1].frame_align=64;
        p.functions[1].args=vec![Slot{offset:if size==0 {0}else{32},size}];p.functions[1].result=p.functions[1].args[0];
        same(&p,&[],Limits::default());
        for persistent in [false,true] {
            let l=options(persistent);let mut prepared=PreparedJit::new(&p,&l).unwrap();
            let want=execute_with_engine(&p,&[],Limits::default(),Engine::Interpreter);
            compare(&want,prepared.execute(&[],l.clone()));
            let run=prepared.execute(&[],l).unwrap();assert_eq!(run.jit_resumable_calls,1);compare(&want,Ok(run));
        }
    }
}

#[test]
fn native_indirect_recursion_and_unavailable_entry_remain_bounded() {
    let mut p=fixture(4);p.functions[1].registers=2;
    p.functions[1].code=vec![Op::Local{dst:0,offset:8},Op::Imm{dst:1,value:pointer(1)},
        Op::CallIndirect{callee:1,args:vec![0],arg_sizes:vec![8],destination:0,result_size:8},Op::Return];
    for frames in [1,2,4,16] {same(&p,&[pointer(1)],Limits{frames,instructions:1000,..Limits::default()});}
    for instructions in [1,8,12,20,100] {same(&p,&[pointer(1)],Limits{instructions,..Limits::default()});}
    p.functions[1].code=vec![Op::Trap{message:"unavailable native entry".into()}];
    same(&p,&[pointer(1)],Limits::default());
}

#[test]
fn native_indirect_explicit_mode_and_prepared_identity() {
    let p=fixture(4);
    let wrong=Limits{jit_indirect_calls:true,..Limits::default()};
    assert_eq!(execute_with_engine(&p,&[pointer(1)],wrong,Engine::Jit).unwrap_err(),"native indirect calls require resumable calls");
    assert!(execute_with_engine(&p,&[pointer(1)],options(false),Engine::Interpreter).unwrap_err().contains("JIT engine"));
    for enabled in [false,true] {
        let l=Limits{jit_indirect_calls:enabled,..options(false)};let mut prepared=PreparedJit::new(&p,&l).unwrap();
        let changed=Limits{jit_indirect_calls:!enabled,..l};
        assert_eq!(prepared.execute(&[pointer(1)],changed).unwrap_err(),"prepared JIT code-generation options changed");
    }
}

#[test]
fn native_indirect_operation_map_reconstructs_published_transitions() {
    let p=fixture(4);let path=std::env::temp_dir().join(format!("rust-indirect-map-{}-{}",std::process::id(),
        std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_nanos()));
    let (run,profile)=execute_profiled(&p,&[pointer(1)],Limits{jit_code_dump:Some(path.clone()),jit_operation_map:true,..options(true)},Engine::Jit).unwrap();
    let map:serde_json::Value=serde_json::from_slice(&std::fs::read(path.join("map.json")).unwrap()).unwrap();
    let ops:serde_json::Value=serde_json::from_slice(&std::fs::read(path.join("operations.json")).unwrap()).unwrap();
    assert_eq!(map["indirect_calls"],true);assert_eq!(ops["indirect_calls"],true);
    assert_eq!(ops["reconstructed_bytes_match"],true);assert_eq!(map["code_bytes"],run.jit_bytes);
    assert!(map["ranges"].as_array().unwrap().iter().any(|r|r["kind"]=="resumable_indirect_call"));
    assert_eq!(profile.functions[0].jit_block_ends[6],7);
    std::fs::remove_dir_all(path).unwrap();
}
