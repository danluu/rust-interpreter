use super::*;
use crate::{Binary, Function, Op, Slot, FUNCTION_POINTER_TAG, HEAP_POINTER_TAG};

fn f(code:Vec<Op>,registers:usize,args:Vec<Slot>,result:Slot,frame_size:usize)->Function {
    Function{name:"scalar-test".into(),frame_size,frame_align:16,registers,args,result,code}
}
fn slot(offset:usize,size:usize)->Slot {Slot{offset,size}}
fn artifact(functions:Vec<Function>,abi:Vec<FunctionAbi>)->Artifact {
    Artifact::scalar(Program{version:VERSION,target:"aarch64-apple-darwin".into(),entry:0,functions,
        data:vec![],statics:vec![],thread_locals:vec![]},abi).unwrap()
}
fn memory_abi(f:&Function)->FunctionAbi {FunctionAbi{arguments:vec![None;f.args.len()],result:None}}

// Independent memory-ABI adapter: explicit entry loads and return stores using
// the existing VM. Probe-body promotion is never used as an execution oracle.
fn legacy(a:&Artifact)->Program {
    let mut p=a.program.clone();p.version=VERSION;
    for (f,abi) in p.functions.iter_mut().zip(&a.scalar_abi) {
        if abi.arguments.iter().all(Option::is_none) && abi.result.is_none() {continue;}
        let scratch=f.registers as u32;f.registers+=1;
        let original=std::mem::take(&mut f.code);let mut code=vec![];
        if let Some(result)=abi.result {code.push(Op::Imm{dst:result,value:0});}
        for (s,r) in f.args.iter().zip(&abi.arguments) {
            if let Some(r)=r {code.extend([Op::Local{dst:scratch,offset:s.offset},Op::Load{dst:*r,address:scratch,size:s.size as u8}]);}
        }
        let mut map=vec![0;original.len()];
        for (pc,op) in original.into_iter().enumerate() {
            map[pc]=code.len();
            if matches!(op,Op::Return) {
                if let Some(result)=abi.result {code.extend([Op::Local{dst:scratch,offset:f.result.offset},Op::Store{address:scratch,src:result,size:f.result.size as u8}]);}
            }
            code.push(op);
        }
        for op in &mut code {
            match op {
                Op::Jump{target}=>*target=map[*target],
                Op::Switch{cases,otherwise,..}=>{for (_,target) in cases {*target=map[*target];}*otherwise=map[*otherwise];},
                _=>{},
            }
        }
        f.code=code;
    }
    crate::validate(&p).unwrap();p
}

fn check(a:&Artifact,args:&[u128],want:u128) {
    let ordinary=crate::execute(&legacy(a),args,Limits::default()).unwrap();assert_eq!(ordinary.value,want);
    let run=a.execute(args,Limits::default()).unwrap();assert_eq!(run.value,want);
    let (observed,profile)=a.execute_profiled(args,Limits::default(),Engine::Interpreter).unwrap();
    assert_eq!((observed.value,observed.instructions),(run.value,run.instructions));
    assert_eq!(profile.functions.iter().flat_map(|f|&f.interpreted).sum::<u64>(),run.instructions);
    for budget in [0,run.instructions-1,run.instructions,run.instructions+1] {
        let result=a.execute(args,Limits{instructions:budget,..Limits::default()});
        if budget<run.instructions {assert_eq!(result.unwrap_err(),"interpreter instruction limit exceeded");}
        else {assert_eq!(result.unwrap().value,want);}
    }
}

#[test]
fn scalar_root_widths_aliases_and_upper_bits() {
    for size in [1,2,4,8,16] {
        let a=artifact(vec![f(vec![Op::Return],1,vec![slot(0,size)],slot(0,size),16)],
            vec![FunctionAbi{arguments:vec![Some(0)],result:Some(0)}]);
        let max=if size==16 {u128::MAX} else {(1u128<<(size*8))-1};
        check(&a,&[max],max);check(&a,&[0],0);
        if size<16 {assert_eq!(a.execute(&[max+1],Limits::default()).unwrap_err(),"entry argument exceeds its integer width");}
        let b=artifact(vec![f(vec![Op::Imm{dst:0,value:u128::MAX},Op::Return],1,vec![],slot(0,size),16)],
            vec![FunctionAbi{arguments:vec![],result:Some(0)}]);
        check(&b,&[],max);
    }
}

fn mixed(indirect:bool)->Artifact {
    let mut code=vec![Op::Local{dst:0,offset:0},Op::Local{dst:1,offset:16},Op::Imm{dst:2,value:11},
        Op::Store{address:1,src:2,size:8},Op::Local{dst:3,offset:32},Op::Imm{dst:4,value:7},Op::Store{address:3,src:4,size:8}];
    if indirect {code.push(Op::Imm{dst:5,value:(FUNCTION_POINTER_TAG|2) as u128});
        code.push(Op::CallIndirect{callee:5,args:vec![1,3],arg_sizes:vec![8,8],destination:0,result_size:8});}
    else {code.push(Op::Call{function:1,args:vec![1,3],destination:0});}
    code.push(Op::Return);
    let root=f(code,6,vec![],slot(0,8),48);
    let child=f(vec![Op::Local{dst:0,offset:16},Op::Load{dst:2,address:0,size:8},
        Op::Binary{dst:3,overflow:0,op:Binary::Add,a:1,b:2,bits:64,signed:false},Op::Return],
        4,vec![slot(0,8),slot(16,8)],slot(32,8),48);
    let abi=vec![memory_abi(&root),FunctionAbi{arguments:vec![Some(1),None],result:Some(3)}];
    artifact(vec![root,child],abi)
}

#[test]
fn scalar_direct_and_indirect_mixed_calls() {
    for indirect in [false,true] {check(&mixed(indirect),&[],18);}
}

#[test]
fn scalar_results_are_initialized_on_reused_backing() {
    let root=f(vec![Op::Local{dst:0,offset:0},Op::Local{dst:1,offset:16},Op::Imm{dst:2,value:1},Op::Store{address:1,src:2,size:8},
        Op::Call{function:1,args:vec![1],destination:0},Op::Imm{dst:2,value:0},Op::Store{address:1,src:2,size:8},
        Op::Call{function:1,args:vec![1],destination:0},Op::Return],3,vec![],slot(0,8),32);
    let child=f(vec![Op::Switch{value:0,cases:vec![(0,3)],otherwise:1},Op::Imm{dst:1,value:99},Op::Return,Op::Return],
        2,vec![slot(0,8)],slot(16,8),32);
    assert!(!crate::registers::needs_initial_zeroes_with_inputs(&child,&[0,1]));
    let abi=vec![memory_abi(&root),FunctionAbi{arguments:vec![Some(0)],result:Some(1)}];
    check(&artifact(vec![root,child],abi),&[],0);
}

#[test]
fn scalar_recursion_preserves_parent_values() {
    let child=f(vec![Op::Switch{value:0,cases:vec![(0,10)],otherwise:1},Op::Imm{dst:5,value:1},
        Op::Binary{dst:5,overflow:4,op:Binary::Sub,a:0,b:5,bits:64,signed:false},
        Op::Local{dst:2,offset:32},Op::Store{address:2,src:5,size:8},Op::Local{dst:3,offset:16},
        Op::Call{function:0,args:vec![2],destination:3},Op::Load{dst:1,address:3,size:8},
        Op::Binary{dst:1,overflow:4,op:Binary::Add,a:0,b:1,bits:64,signed:false},Op::Return,
        Op::Imm{dst:1,value:0},Op::Return],6,vec![slot(0,8)],slot(16,8),48);
    let a=artifact(vec![child],vec![FunctionAbi{arguments:vec![Some(0)],result:Some(1)}]);
    for n in [0,1,2,7,12] {check(&a,&[n],n*(n+1)/2);}
    assert_eq!(a.execute(&[2],Limits{frames:1,..Limits::default()}).unwrap_err(),"interpreter call-depth limit exceeded");
}

#[test]
fn scalar_tls_callback_input_and_reset_lifecycle() {
    let root=f(vec![Op::Imm{dst:0,value:(FUNCTION_POINTER_TAG|2) as u128},Op::Imm{dst:1,value:(HEAP_POINTER_TAG|16) as u128},
        Op::RegisterTlsDestructor{callback:0,argument:1},Op::ResetThreadLocals,Op::Load{dst:3,address:1,size:8},Op::Return],
        4,vec![],slot(0,8),16);
    let callback=f(vec![Op::Imm{dst:1,value:7},Op::Store{address:0,src:1,size:8},Op::Return],2,vec![slot(0,8)],slot(0,0),16);
    let mut a=artifact(vec![root,callback],vec![FunctionAbi{arguments:vec![],result:Some(3)},FunctionAbi{arguments:vec![Some(0)],result:None}]);
    a.program.statics=vec![0;32];check(&a,&[],7);
}

#[test]
fn scalar_call_fault_order_matches_memory_reference() {
    let mut a=mixed(false);
    // First source fails before a call-depth failure, as in the memory ABI.
    a.program.functions[0].code[1]=Op::Imm{dst:1,value:usize::MAX as u128};
    a.program.functions[0].code[3]=Op::Imm{dst:2,value:11};
    for frames in [1,2] {
        let ours=a.execute(&[],Limits{frames,..Limits::default()}).unwrap_err();
        let theirs=crate::execute(&legacy(&a),&[],Limits{frames,..Limits::default()}).unwrap_err();
        assert_eq!(ours,theirs);assert_ne!(ours,"interpreter call-depth limit exceeded");
    }
    // A second argument fault follows the first scalar input read.
    let mut a=mixed(false);a.program.functions[0].code[4]=Op::Imm{dst:3,value:usize::MAX as u128};
    a.program.functions[0].code[6]=Op::Imm{dst:4,value:7};
    assert_eq!(a.execute(&[],Limits::default()).unwrap_err(),crate::execute(&legacy(&a),&[],Limits::default()).unwrap_err());
    // Return destinations are checked after callee execution.
    let mut a=mixed(false);a.program.functions[0].code[0]=Op::Imm{dst:0,value:usize::MAX as u128};
    assert_eq!(a.execute(&[],Limits::default()).unwrap_err(),crate::execute(&legacy(&a),&[],Limits::default()).unwrap_err());
}

#[test]
fn scalar_indirect_signatures_and_engine_options_stay_explicit() {
    let mut a=mixed(true);
    if let Op::CallIndirect{result_size,..}=&mut a.program.functions[0].code[8] {*result_size=16;} else {panic!("fixture call moved");}
    assert_eq!(a.execute(&[],Limits::default()).unwrap_err(),"guest function pointer signature mismatch");
    let a=mixed(false);
    assert_eq!(a.execute_with_engine(&[],Limits::default(),Engine::Jit).unwrap_err(),"scalar ABI JIT execution is not implemented");
    assert_eq!(a.execute(&[],Limits{jit_resumable_calls:true,..Limits::default()}).unwrap_err(),"resumable calls require the JIT engine");
    assert!(crate::execute(&a.program,&[],Limits::default()).is_err());
}

#[test]
fn scalar_input_proof_keeps_noninput_reads_initialized() {
    let body=f(vec![Op::Binary{dst:1,overflow:2,op:Binary::Add,a:0,b:1,bits:64,signed:false},Op::Return],3,
        vec![slot(0,8)],slot(16,8),32);
    assert!(crate::registers::needs_initial_zeroes_with_inputs(&body,&[0]));
    assert!(!crate::registers::needs_initial_zeroes_with_inputs(&body,&[0,1]));
    let a=artifact(vec![body],vec![FunctionAbi{arguments:vec![Some(0)],result:Some(1)}]);check(&a,&[9],9);
}
