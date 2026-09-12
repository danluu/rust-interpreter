use super::*;

fn duplicate(l:&Limits)->Limits {
    Limits{memory:l.memory,allocations:l.allocations,instructions:l.instructions,frames:l.frames,
        jit_code_bytes:l.jit_code_bytes,jit_native_calls:l.jit_native_calls,
        jit_native_call_stubs:l.jit_native_call_stubs,jit_persistent_registers:l.jit_persistent_registers,
        jit_resumable_calls:l.jit_resumable_calls,jit_code_dump:l.jit_code_dump.clone()}
}


fn options(resumable:bool,persistent:bool)->Limits {
    Limits{jit_resumable_calls:resumable,jit_persistent_registers:persistent,..Limits::default()}
}
fn expanded(p:&ExecutionProfile)->Vec<Vec<u64>> {
    p.functions.iter().map(|f| {
        let mut hits=f.interpreted.clone();
        for (start,&count) in f.jit_blocks.iter().enumerate() {
            if count!=0 {
                let end=f.jit_block_ends[start];assert!(end>start && end<=hits.len());
                for hit in &mut hits[start..end] {*hit+=count;}
            }
        }
        assert!(f.jit_tree_blocks.iter().all(|&n|n==0));hits
    }).collect()
}
// The existing engines use different diagnostics for the same memory fault.
// Normalize only these exact messages; depth, budget and all other failures
// retain their full identity, so their precedence still has to agree.
fn fault(error:String)->String {
    if error=="JIT guest memory access failed" {"invalid guest memory access".into()} else {error}
}
fn outcome(e:Result<Execution,String>)->Result<(u128,u64,usize),String> {
    e.map(|e|(e.value,e.instructions,e.peak_memory)).map_err(fault)
}

pub(super) fn compare(a:&Artifact,args:&[u128],want:u128) {
    let (reference,profile)=a.execute_profiled(args,Limits::default(),Engine::Interpreter).unwrap();
    assert_eq!(reference.value,want);
    for resumable in [false,true] {for persistent in [false,true] {
        let limits=options(resumable,persistent);
        let (native,observed)=a.execute_profiled(args,duplicate(&limits),Engine::Jit).unwrap();
        assert_eq!((native.value,native.instructions,native.peak_memory),
            (reference.value,reference.instructions,reference.peak_memory));
        assert_eq!(expanded(&observed),expanded(&profile));
        for budget in 0..=reference.instructions+1 {
            let limits=Limits{instructions:budget,..duplicate(&limits)};
            let ordinary=a.execute(args,Limits{instructions:budget,..Limits::default()});
            let unprofiled=a.execute_with_engine(args,duplicate(&limits),Engine::Jit);
            let profiled=a.execute_profiled(args,limits,Engine::Jit).map(|(e,_)|e);
            let expected=outcome(ordinary);
            assert_eq!(outcome(unprofiled),expected,"budget={budget}, resumable={resumable}, persistent={persistent}");
            assert_eq!(outcome(profiled),expected,"profile budget={budget}");
        }
    }}
}

fn hot(size:usize,input:u128,alias:bool)->Artifact {
    let root=f(vec![Op::Local{dst:0,offset:0},Op::Local{dst:1,offset:16},Op::Imm{dst:2,value:input},
        Op::Store{address:1,src:2,size:size as u8},Op::Call{function:1,args:vec![1],destination:0},
        Op::Call{function:1,args:vec![1],destination:0},Op::Return],3,vec![],slot(0,size),32);
    let result=if alias{0}else{1};
    let child=f(vec![Op::Imm{dst:2,value:u128::MAX},
        Op::Binary{dst:result,overflow:3,op:Binary::Xor,a:0,b:2,bits:128,signed:false},Op::Return],
        4,vec![slot(0,size)],slot(16,size),32);
    let abi=vec![memory_abi(&root),FunctionAbi{arguments:vec![Some(0)],result:Some(result)}];
    artifact(vec![root,child],abi)
}

#[test]
fn scalar_native_hot_calls_cover_all_widths_and_input_result_aliases() {
    for size in [1,2,4,8,16] {for alias in [false,true] {
        let input=if size==16 {0x123456789abcdef0123456789abcdef0} else {0x53};
        let a=hot(size,input,alias);let want=crate::scalar_abi::truncate(!input,size);
        compare(&a,&[],want);
        for persistent in [false,true] {
            let e=a.execute_with_engine(&[],options(true,persistent),Engine::Jit).unwrap();
            assert!(e.jit_resumable_calls>=1);assert!(e.jit_resumable_returns>=2);
        }
    }}
}

#[test]
fn scalar_native_result_lives_across_backedges_and_vm_return() {
    // Both the loop update and the final Return read r0. Its last explicit
    // read precedes the last write, which exposed ordinary forwarding loss.
    let body=f(vec![Op::Imm{dst:1,value:1},Op::Imm{dst:2,value:7},
        Op::Binary{dst:0,overflow:3,op:Binary::Add,a:0,b:1,bits:64,signed:false},
        Op::Binary{dst:4,overflow:3,op:Binary::Lt,a:0,b:2,bits:64,signed:false},
        Op::Switch{value:4,cases:vec![(1,2)],otherwise:5},Op::Return],5,
        vec![slot(0,8)],slot(16,8),32);
    let a=artifact(vec![body],vec![FunctionAbi{arguments:vec![Some(0)],result:Some(0)}]);
    compare(&a,&[0],7);compare(&a,&[9],10);
    let e=a.execute_with_engine(&[0],options(true,true),Engine::Jit).unwrap();
    assert!(e.jit_register_pairs>0);assert!(e.jit_instructions>0);
}

fn compare_failure(a:&Artifact,limits:Limits) {
    let error=fault(a.execute(&[],duplicate(&limits)).unwrap_err());
    for resumable in [false,true] {for persistent in [false,true] {
        let limits=Limits{jit_resumable_calls:resumable,jit_persistent_registers:persistent,..duplicate(&limits)};
        assert_eq!(fault(a.execute_with_engine(&[],duplicate(&limits),Engine::Jit).unwrap_err()),error);
        assert_eq!(fault(a.execute_profiled(&[],limits,Engine::Jit).unwrap_err()),error);
    }}
}

#[test]
fn scalar_native_hot_faults_preserve_argument_return_and_budget_order() {
    for destination in [false,true] {
        let mut a=hot(8,0x53,false);
        a.program.functions[0].code.insert(5,Op::Imm{dst:if destination{0}else{1},value:usize::MAX as u128});
        for budget in 0..=15 {
            let limits=Limits{instructions:budget,..Limits::default()};
            compare_failure(&a,limits);
        }
    }
    // Same source fault vs depth-order check as the interpreter qualification.
    let mut a=mixed(false);a.program.functions[0].code[1]=Op::Imm{dst:1,value:usize::MAX as u128};
    a.program.functions[0].code[3]=Op::Imm{dst:2,value:11};
    for frames in [1,2] {compare_failure(&a,Limits{frames,..Limits::default()});}
}

#[test]
fn scalar_native_code_and_working_limits_keep_interpreter_semantics() {
    let a=hot(16,17,false);
    for code_bytes in [0,4,128,1024,4096] {
        for resumable in [false,true] {for persistent in [false,true] {
            let limits=Limits{jit_code_bytes:code_bytes,..options(resumable,persistent)};
            let e=a.execute_with_engine(&[],limits,Engine::Jit).unwrap();
            assert_eq!(e.value,!17u128);assert!(e.jit_bytes<=code_bytes);
        }}
    }
    for frames in [0,1,2] {for bytes in [0,32,96,192,512] {
        let limits=Limits{frames,memory:bytes,..Limits::default()};
        let want=outcome(a.execute(&[],duplicate(&limits)));
        for persistent in [false,true] {
            let limits=Limits{jit_resumable_calls:true,jit_persistent_registers:persistent,..duplicate(&limits)};
            assert_eq!(outcome(a.execute_with_engine(&[],limits,Engine::Jit)),want);
        }
    }}
}

#[test]
fn scalar_native_indirect_signature_failure_stays_explicit() {
    let mut a=mixed(true);
    if let Op::CallIndirect{result_size,..}=&mut a.program.functions[0].code[8] {*result_size=16;} else {panic!("fixture moved");}
    compare_failure(&a,Limits::default());
}
