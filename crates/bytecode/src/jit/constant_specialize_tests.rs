use super::*;
use crate::{Binary,Engine,Function,Limits,Slot};

fn padding(code:&mut Vec<Op>) {
    code.push(Op::Imm{dst:13,value:0});
    for value in 1..=128 {
        code.extend([Op::Imm{dst:14,value},Op::Binary{dst:13,overflow:15,op:Binary::Add,a:13,b:14,bits:64,signed:false}]);
    }
}
fn program(values:&[u128])->Program {
    let mut code=vec![Op::Local{dst:0,offset:16},Op::Load{dst:1,address:0,size:8},
        Op::Local{dst:2,offset:32},Op::Local{dst:3,offset:40},Op::Local{dst:4,offset:48},Op::Imm{dst:8,value:0}];
    for &value in values {
        code.extend([Op::Imm{dst:5,value},Op::Store{address:2,src:5,size:8},Op::Store{address:3,src:1,size:8},
            Op::Call{function:1,args:vec![2,3],destination:4},Op::Load{dst:7,address:4,size:8},
            Op::Binary{dst:8,overflow:9,op:Binary::Add,a:8,b:7,bits:64,signed:false}]);
    }
    code.extend([Op::Local{dst:0,offset:0},Op::Store{address:0,src:8,size:8},Op::Return]);
    let mut leaf=vec![Op::Local{dst:0,offset:0},Op::Load{dst:1,address:0,size:8},Op::Local{dst:2,offset:8},Op::Load{dst:3,address:2,size:8}];
    padding(&mut leaf);
    leaf.extend([Op::Binary{dst:7,overflow:6,op:Binary::Add,a:1,b:13,bits:64,signed:false},
        Op::Binary{dst:7,overflow:6,op:Binary::Xor,a:7,b:3,bits:64,signed:false},
        Op::Local{dst:0,offset:32},Op::Store{address:0,src:7,size:8},Op::Return]);
    Program{version:crate::VERSION,target:"aarch64-apple-darwin".into(),entry:0,data:vec![0;32],statics:vec![],thread_locals:vec![],functions:vec![
        Function{name:"root".into(),frame_size:64,frame_align:16,registers:16,args:vec![Slot{offset:16,size:8}],result:Slot{offset:0,size:8},code},
        Function{name:"callee".into(),frame_size:64,frame_align:16,registers:16,args:vec![Slot{offset:0,size:8},Slot{offset:8,size:8}],result:Slot{offset:32,size:8},code:leaf}
    ]}
}
fn normalize<T>(result:Result<T,String>)->Result<T,String> {
    result.map_err(|e|match e.as_str() {"invalid guest memory access"|"JIT guest memory access failed"=>"guest memory range fault".into(),_=>e})
}
fn check(p:&Program,arguments:&[u128],clones:bool)->Program {
    let (q,report)=specialize(p.clone()).unwrap();
    assert_eq!(!report["clones"].as_array().unwrap().is_empty(),clones,"{report}");
    assert_eq!(q.data,p.data);assert_eq!(q.statics,p.statics);
    assert_eq!(bincode::serialize(&q.thread_locals).unwrap(),bincode::serialize(&p.thread_locals).unwrap());assert_eq!(q.entry,p.entry);
    for (old,new) in p.functions.iter().zip(&q.functions) {
        let mut expected=old.clone();
        for (op,next) in expected.code.iter_mut().zip(&new.code) {
            if let (Op::Call{function,..},Op::Call{function:target,..})=(op,next) {*function=*target;}
        }
        assert_eq!(bincode::serialize(&expected).unwrap(),bincode::serialize(new).unwrap());
    }
    for f in &q.functions[p.functions.len()..] {
        assert!(f.code.iter().all(|op|!matches!(op,Op::Call{function,..} if *function>=p.functions.len())));
    }
    for &argument in arguments {
        let observe=|p:&Program|crate::execute_with_engine(p,&[argument],Limits::default(),Engine::Interpreter).map(|r|(r.value,r.peak_memory));
        assert_eq!(observe(p),observe(&q));
        for artifact in [p,&q] {
            let result=crate::execute_with_engine(artifact,&[argument],Limits::default(),Engine::Interpreter);
            let n=result.as_ref().map_or(100,|r|r.instructions);
            for resumable in [false,true] {for persistent in [false,true] {for capacity in [0,16*1024*1024] {
                for budget in [0,1,n.saturating_sub(1),n,n+1] {
                    let limits=Limits{instructions:budget,jit_resumable_calls:resumable,jit_persistent_registers:persistent,jit_code_bytes:capacity,..Limits::default()};
                    let run=|engine| {
                        let mut limits=limits.clone();
                        if engine==Engine::Interpreter {limits.jit_resumable_calls=false;limits.jit_persistent_registers=false;}
                        normalize(crate::execute_with_engine(artifact,&[argument],limits,engine).map(|r|(r.value,r.instructions,r.peak_memory)))
                    };
                    assert_eq!(run(Engine::Jit),run(Engine::Interpreter),"resumable={resumable} persistent={persistent} capacity={capacity} budget={budget}");
                }
            }}}
        }
    }
    q
}

#[test]
fn shared_values_get_bounded_clones_and_unique_values_keep_original_calls() {
    check(&program(&[7;8]),&[0,1,u64::MAX as u128],true);
    let p=program(&[1,2,3,4,5,6,7,8]);let q=check(&p,&[9],false);
    assert_eq!(bincode::serialize(&p).unwrap(),bincode::serialize(&q).unwrap());
    check(&program(&[7,7,7,7,9,9,9,9]),&[255],true);
}
#[test]
fn unknown_overlapping_arguments_override_earlier_known_bytes() {
    let mut p=program(&[0x1122334455667788;8]);p.functions[1].args[1].offset=4;
    p.functions[1].code[2]=Op::Local{dst:2,offset:4};
    check(&p,&[0,0x123456789abcdef0,u64::MAX as u128],true);
}
#[test]
fn invalid_argument_copies_still_fault_before_the_specialized_body() {
    let mut p=program(&[7;8]);p.functions[0].code.insert(0,Op::Imm{dst:10,value:0});
    for op in &mut p.functions[0].code {if let Op::Call{args,..}=op {args[1]=10;}}
    check(&p,&[0],true);
}
#[test]
fn opaque_caller_mutation_prevents_stale_argument_facts() {
    let mut p=program(&[7;8]);
    p.functions.push(Function{name:"mutate".into(),frame_size:16,frame_align:8,registers:3,args:vec![Slot{offset:0,size:8}],result:Slot{offset:0,size:0},
        code:vec![Op::Local{dst:0,offset:0},Op::Load{dst:1,address:0,size:8},Op::Imm{dst:2,value:123},Op::Store{address:1,src:2,size:8},Op::Return]});
    let mut code=Vec::new();
    for op in p.functions[0].code.drain(..) {
        if matches!(op,Op::Call{..}) {
            code.extend([Op::Local{dst:10,offset:56},Op::Store{address:10,src:2,size:8},Op::Call{function:2,args:vec![10],destination:4}]);
        }
        code.push(op);
    }
    p.functions[0].code=code;check(&p,&[1],false);
}
#[test]
fn indirect_handles_and_recursive_clones_retain_original_function_identity() {
    let mut p=program(&[3;8]);p.functions[0].code.insert(0,Op::Imm{dst:12,value:(crate::FUNCTION_POINTER_TAG|2) as u128});
    let mut seen=0;
    for op in &mut p.functions[0].code {
        if let Op::Call{args,destination,..}=op {
            seen+=1;if seen%2==0 {*op=Op::CallIndirect{callee:12,args:args.clone(),arg_sizes:vec![8,8],destination:*destination,result_size:8};}
        }
    }
    check(&p,&[31],true);
    let mut code=vec![Op::Local{dst:0,offset:0},Op::Load{dst:1,address:0,size:8},Op::Imm{dst:2,value:0},
        Op::Binary{dst:3,overflow:4,op:Binary::Eq,a:1,b:2,bits:64,signed:false},Op::Switch{value:3,cases:vec![(1,0)],otherwise:5}];
    padding(&mut code);
    code.extend([Op::Local{dst:5,offset:48},Op::Imm{dst:6,value:1},Op::Binary{dst:7,overflow:8,op:Binary::Sub,a:1,b:6,bits:64,signed:false},
        Op::Store{address:5,src:7,size:8},Op::Local{dst:9,offset:8},Op::Local{dst:10,offset:32},
        Op::Call{function:1,args:vec![5,9],destination:10},Op::Load{dst:11,address:10,size:8},
        Op::Binary{dst:11,overflow:12,op:Binary::Add,a:11,b:6,bits:64,signed:false},Op::Store{address:10,src:11,size:8},Op::Return]);
    let base=code.len();if let Op::Switch{cases,..}=&mut code[4] {cases[0].1=base;}
    code.extend([Op::Local{dst:10,offset:32},Op::Local{dst:9,offset:8},Op::Load{dst:11,address:9,size:8},Op::Store{address:10,src:11,size:8},Op::Return]);
    p.functions[1].code=code;check(&p,&[7],true);
}
#[test]
fn shape_and_code_growth_declines_preserve_program_bytes() {
    let mut p=program(&[7;8]);p.functions[1].code=vec![Op::Return;513];
    let (q,r)=specialize(p.clone()).unwrap();assert!(r["clones"].as_array().unwrap().is_empty());
    assert_eq!(bincode::serialize(&p).unwrap(),bincode::serialize(&q).unwrap());
    let mut p=program(&[7,7]);p.functions[1].code=vec![Op::Return];
    let (q,r)=specialize(p.clone()).unwrap();assert!(r["clones"].as_array().unwrap().is_empty());
    assert_eq!(bincode::serialize(&p).unwrap(),bincode::serialize(&q).unwrap());
    let mut p=program(&[7,7]);
    for _ in 0..32 {p.functions[1].code.insert(4,Op::Store{address:0,src:1,size:8});}
    let (q,r)=specialize(p.clone()).unwrap();assert!(r["clones"].as_array().unwrap().is_empty());
    assert!(r["attempts"].as_array().unwrap().iter().any(|a|a["reason"]=="code growth limit"));
    assert_eq!(bincode::serialize(&p).unwrap(),bincode::serialize(&q).unwrap());
}

#[test]
fn a_backedge_to_entry_discards_argument_facts_changed_by_the_loop() {
    let mut p=program(&[3;8]);
    let mut code=vec![Op::Local{dst:0,offset:0},Op::Load{dst:1,address:0,size:8},Op::Imm{dst:2,value:0},
        Op::Binary{dst:3,overflow:4,op:Binary::Eq,a:1,b:2,bits:64,signed:false},Op::Switch{value:3,cases:vec![(1,0)],otherwise:5}];
    padding(&mut code);
    code.extend([Op::Imm{dst:6,value:1},Op::Binary{dst:7,overflow:8,op:Binary::Sub,a:1,b:6,bits:64,signed:false},
        Op::Store{address:0,src:7,size:8},Op::Jump{target:0}]);
    let exit=code.len();if let Op::Switch{cases,..}=&mut code[4] {cases[0].1=exit;}
    code.extend([Op::Local{dst:9,offset:8},Op::Load{dst:11,address:9,size:8},Op::Local{dst:10,offset:32},
        Op::Store{address:10,src:11,size:8},Op::Return]);
    p.functions[1].code=code;check(&p,&[0,255],true);
}
