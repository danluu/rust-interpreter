use super::*;
use crate::{CallArgument as A, CallDestination as D};

// Independent adapter to the already qualified address ABI, then to version 5.
// It deliberately materializes caller slots; it never runs scalar promotion.
fn memory_reference(a:&Artifact)->Program {
    let mut bridge=a.clone();
    for f in &mut bridge.program.functions {
        let extra=f.code.iter().filter_map(|op|match op {Op::CallValue{args,..}=>Some(args.len()+1),_=>None}).max().unwrap_or(0);
        if extra==0 {continue;}
        let base=f.frame_size.next_multiple_of(16);let scratch=f.registers as u32;
        f.frame_size=base+16*extra;f.registers+=extra;
        let old=std::mem::take(&mut f.code);let mut code=vec![];let mut map=vec![0;old.len()];
        for (pc,op) in old.into_iter().enumerate() {
            map[pc]=code.len();
            if let Op::CallValue{function,args,destination}=op {
                let callee=&a.program.functions[function];let mut addresses=vec![];
                for (i,(arg,slot)) in args.iter().zip(&callee.args).enumerate() {
                    match arg {
                        A::Address(r)=>addresses.push(*r),
                        A::Value(r)=>{let address=scratch+i as u32;code.extend([
                            Op::Local{dst:address,offset:base+16*i},Op::Store{address,src:*r,size:slot.size as u8}]);addresses.push(address);}
                    }
                }
                let dst=match destination {D::Address(r)=>r,D::Value(_)=>{
                    let r=scratch+args.len() as u32;code.push(Op::Local{dst:r,offset:base+16*args.len()});r}};
                code.push(Op::Call{function,args:addresses,destination:dst});
                if let D::Value(r)=destination {code.push(Op::Load{dst:r,address:dst,size:callee.result.size as u8});}
            } else {code.push(op);}
        }
        for op in &mut code {match op {
            Op::Jump{target}=>*target=map[*target],
            Op::Switch{cases,otherwise,..}=>{for (_,target) in cases {*target=map[*target];}*otherwise=map[*otherwise];},
            _=>{},
        }}
        f.code=code;
    }
    legacy(&bridge)
}
fn verify(a:&Artifact,args:&[u128],want:u128) {
    let p=memory_reference(a);assert_eq!(crate::execute(&p,args,Limits::default()).unwrap().value,want);
    let bytes=a.encode().unwrap();let decoded=Artifact::decode(&bytes).unwrap();assert_eq!(decoded.encode().unwrap(),bytes);
    native::compare(&decoded,args,want);
}
fn mode(persistent:bool)->Limits {Limits{jit_resumable_calls:true,jit_persistent_registers:persistent,..Limits::default()}}

fn pair(size:usize,value_arg:bool,register_formal:bool,value_destination:bool,register_result:bool,alias:bool)->Artifact {
    let input=0xfedcba98765432100123456789abcdefu128;
    let destination=if value_destination {D::Value(if alias{0}else{3})} else {D::Address(2)};
    let arg=if value_arg{A::Value(0)}else{A::Address(1)};
    let mut code=vec![Op::Imm{dst:0,value:input},Op::Local{dst:1,offset:16},Op::Local{dst:2,offset:0}];
    if !value_arg {code.push(Op::Store{address:1,src:0,size:size as u8});}
    code.push(Op::CallValue{function:1,args:vec![arg],destination});
    code.push(Op::Imm{dst:0,value:input});
    code.push(Op::CallValue{function:1,args:vec![arg],destination});
    if !value_destination {code.push(Op::Load{dst:3,address:2,size:size as u8});}
    code.push(Op::Return);
    let root=f(code,4,vec![],slot(0,size),32);
    let mut code=vec![];
    if !register_formal {code.extend([Op::Local{dst:2,offset:0},Op::Load{dst:0,address:2,size:size as u8}]);}
    code.extend([Op::Imm{dst:1,value:u128::MAX},Op::Binary{dst:0,overflow:3,op:Binary::Xor,a:0,b:1,bits:128,signed:false}]);
    if !register_result {code.extend([Op::Local{dst:2,offset:16},Op::Store{address:2,src:0,size:size as u8}]);}
    code.push(Op::Return);
    let child=f(code,4,vec![slot(0,size)],slot(16,size),32);
    artifact(vec![root,child],vec![FunctionAbi{arguments:vec![],result:Some(if value_destination&&alias{0}else{3})},
        FunctionAbi{arguments:vec![register_formal.then_some(0)],result:register_result.then_some(0)}])
}

#[test]
fn value_call_storage_matrix_widths_and_hot_native_transitions() {
    for size in [1,2,4,8,16] {for va in [false,true] {for formal in [false,true] {for vd in [false,true] {for result in [false,true] {
        let a=pair(size,va,formal,vd,result,vd);let want=crate::scalar_abi::truncate(!0xfedcba98765432100123456789abcdefu128,size);
        verify(&a,&[],want);
        for persistent in [false,true] {
            let e=a.execute_with_engine(&[],mode(persistent),Engine::Jit).unwrap();
            assert!(e.jit_resumable_calls>0);assert!(e.jit_resumable_returns>=2);
        }
    }}}}}
}

#[test]
fn value_call_recursive_register_arguments_preserve_parent_values() {
    let body=f(vec![Op::Switch{value:0,cases:vec![(0,6)],otherwise:1},Op::Imm{dst:2,value:1},
        Op::Binary{dst:2,overflow:3,op:Binary::Sub,a:0,b:2,bits:64,signed:false},
        Op::CallValue{function:0,args:vec![A::Value(2)],destination:D::Value(1)},
        Op::Binary{dst:1,overflow:3,op:Binary::Add,a:0,b:1,bits:64,signed:false},Op::Return,
        Op::Imm{dst:1,value:0},Op::Return],4,vec![slot(0,8)],slot(16,8),32);
    let a=artifact(vec![body],vec![FunctionAbi{arguments:vec![Some(0)],result:Some(1)}]);
    for n in [0,1,2,7,17] {verify(&a,&[n],n*(n+1)/2);}
    let e=a.execute_with_engine(&[17],mode(true),Engine::Jit).unwrap();assert_eq!(e.jit_resumable_calls,17);
}

#[test]
fn value_call_mixed_arguments_and_reused_return_tags() {
    let root=f(vec![Op::Imm{dst:0,value:11},Op::Imm{dst:1,value:7},Op::Local{dst:2,offset:16},
        Op::Store{address:2,src:1,size:8},Op::Local{dst:3,offset:0},Op::Store{address:3,src:0,size:8},
        Op::CallValue{function:1,args:vec![A::Value(0),A::Address(2)],destination:D::Value(4)},
        Op::Call{function:1,args:vec![3,2],destination:3},Op::Load{dst:0,address:3,size:8},
        Op::Imm{dst:5,value:(FUNCTION_POINTER_TAG|2) as u128},
        Op::CallIndirect{callee:5,args:vec![3,2],arg_sizes:vec![8,8],destination:3,result_size:8},
        Op::Load{dst:0,address:3,size:8},
        Op::CallValue{function:1,args:vec![A::Value(0),A::Address(2)],destination:D::Value(4)},Op::Return],
        6,vec![],slot(0,8),32);
    let child=f(vec![Op::Local{dst:2,offset:0},Op::Load{dst:0,address:2,size:8},
        Op::Binary{dst:0,overflow:2,op:Binary::Add,a:0,b:1,bits:64,signed:false},Op::Return],
        3,vec![slot(0,8),slot(16,8)],slot(0,8),32);
    let a=artifact(vec![root,child],vec![FunctionAbi{arguments:vec![],result:Some(4)},
        FunctionAbi{arguments:vec![None,Some(1)],result:Some(0)}]);
    verify(&a,&[],32);
    let e=a.execute_with_engine(&[],mode(true),Engine::Jit).unwrap();assert!(e.jit_resumable_calls>=2);
}

#[test]
fn value_call_metadata_and_opcode_validation_precede_execution() {
    let a=pair(8,true,true,true,true,false);
    for version in [VERSION,VERSION|crate::PARTIAL_VALIDATION] {
        let mut p=a.program.clone();p.version=version;
        assert!(crate::validate(&p).unwrap_err().contains("value calls require scalar artifact version 6"));
    }
    for change in 0..5 {
        let mut bad=a.clone();let op=bad.program.functions[0].code.iter_mut().find(|op|matches!(op,Op::CallValue{..})).unwrap();
        if let Op::CallValue{function,args,destination}=op {match change {
            0=>*function=999,1=>args.clear(),2=>args[0]=A::Value(999),3=>*destination=D::Value(999),
            4=>*destination=D::Address(999),_=>unreachable!(),
        }}
        assert!(bad.validate().is_err());assert!(Artifact::decode(&bincode::serialize(&bad).unwrap()).is_err());
        assert!(bad.execute_with_engine(&[],mode(true),Engine::Jit).is_err());
    }
    for result in [false,true] {
        let mut bad=a.clone();let callee=&mut bad.program.functions[1];
        if result {callee.result.size=0;bad.scalar_abi[1].result=None;}
        else {callee.args[0].size=0;bad.scalar_abi[1].arguments[0]=None;}
        assert!(bad.validate().unwrap_err().contains("value call"));
    }
}

#[test]
fn value_call_result_is_a_definition_and_aliased_inputs_are_reads() {
    let op=Op::CallValue{function:0,args:vec![A::Value(3),A::Address(2)],destination:D::Value(3)};
    let(mut reads,mut writes)=(vec![],vec![]);crate::diagnostic_visit_registers(&op,|r|reads.push(r),|r|writes.push(r));
    assert_eq!(reads,vec![3,2]);assert_eq!(writes,vec![3]);
    let op=Op::CallValue{function:0,args:vec![],destination:D::Value(0)};
    let body=f(vec![op,Op::Assert{value:0,expected:false,message:"result".into()},Op::Return],1,vec![],slot(0,0),16);
    assert!(!crate::registers::needs_initial_zeroes(&body));
}

#[test]
fn value_call_faults_and_limits_retain_order() {
    let mut a=pair(8,true,true,true,true,false);
    let second=a.program.functions[0].code.iter().enumerate().filter_map(|(pc,op)|matches!(op,Op::CallValue{..}).then_some(pc)).nth(1).unwrap();
    a.program.functions[0].code.insert(second,Op::Imm{dst:1,value:usize::MAX as u128});
    if let Op::CallValue{args,..}=&mut a.program.functions[0].code[second+1] {args[0]=A::Address(1);}
    for budget in 0..20 {
        let expected=native::outcome(a.execute(&[],Limits{instructions:budget,..Limits::default()}));
        for persistent in [false,true] {assert_eq!(native::outcome(a.execute_with_engine(&[],Limits{instructions:budget,..mode(persistent)},Engine::Jit)),expected);}
    }
    let a=pair(16,true,true,true,true,true);
    for bytes in [0,64,128,256,512] {for frames in [0,1,2] {for code in [0,4,512,4096] {
        let expected=native::outcome(a.execute(&[],Limits{memory:bytes,frames,..Limits::default()}));
        assert_eq!(native::outcome(a.execute_with_engine(&[],Limits{memory:bytes,frames,jit_code_bytes:code,..mode(true)},Engine::Jit)),expected);
    }}}
}

#[test]
fn value_call_tls_callback_resets_reused_tag_and_calls_scalar_child() {
    let root=f(vec![Op::Imm{dst:0,value:(FUNCTION_POINTER_TAG|2) as u128},
        Op::Imm{dst:1,value:(HEAP_POINTER_TAG|16) as u128},Op::RegisterTlsDestructor{callback:0,argument:1},
        Op::Imm{dst:2,value:5},Op::CallValue{function:2,args:vec![A::Value(2)],destination:D::Value(3)},
        Op::ResetThreadLocals,Op::Load{dst:3,address:1,size:8},Op::Return],4,vec![],slot(0,8),16);
    let callback=f(vec![Op::Imm{dst:1,value:11},
        Op::CallValue{function:2,args:vec![A::Value(1)],destination:D::Value(2)},
        Op::Store{address:0,src:2,size:8},Op::Return],3,vec![slot(0,8)],slot(0,0),16);
    let leaf=f(vec![Op::Imm{dst:1,value:7},Op::Binary{dst:0,overflow:2,op:Binary::Add,a:0,b:1,bits:64,signed:false},Op::Return],
        3,vec![slot(0,8)],slot(0,8),16);
    let mut a=artifact(vec![root,callback,leaf],vec![FunctionAbi{arguments:vec![],result:Some(3)},
        FunctionAbi{arguments:vec![Some(0)],result:None},FunctionAbi{arguments:vec![Some(0)],result:Some(0)}]);
    a.program.statics=vec![0;32];verify(&a,&[],18);
    assert!(a.execute_with_engine(&[],mode(true),Engine::Jit).unwrap().jit_resumable_calls>0);
}
