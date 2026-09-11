use super::*;
use rust_interp_bytecode::{Binary,Engine,Function,Limits,Program,VERSION,execute_with_engine,execute_profiled,validate};
fn function(code:Vec<Op>,registers:usize)->Function {
    Function{name:"scalar-promotion".into(),frame_size:64,frame_align:16,registers,args:vec![],result:Slot{offset:0,size:16},code}
}
fn program(f:Function)->Program {
    Program{version:VERSION,target:"aarch64-apple-darwin".into(),entry:0,functions:vec![f],data:vec![],statics:vec![],thread_locals:vec![]}
}
fn transformed(p:&Program,slots:&[Slot])->(Program,Report) {
    let mut out=p.clone();let f=&mut out.functions[0];let mut count=f.registers as u32;
    let r=promote(&mut f.code,&mut count,slots);f.registers=count as usize;validate(&out).unwrap();(out,r)
}
fn engines()->Vec<Engine> {
    let mut v=vec![Engine::Interpreter];if cfg!(all(target_arch="aarch64",target_os="macos")){v.push(Engine::Jit);}v
}
fn check(p:&Program,args:&[u128],expected:u128) {
    for engine in engines() {for capacity in [0,16*1024*1024] {
        let limits=||Limits{jit_code_bytes:capacity,..Limits::default()};
        let r=execute_with_engine(p,args,limits(),engine).unwrap();assert_eq!(r.value,expected);
        let (observed,_)=execute_profiled(p,args,limits(),engine).unwrap();assert_eq!((observed.value,observed.instructions),(r.value,r.instructions));
        for budget in [0,r.instructions-1,r.instructions,r.instructions+1] {
            let value=execute_with_engine(p,args,Limits{instructions:budget,..limits()},engine);
            if budget<r.instructions {assert_eq!(value.unwrap_err(),"interpreter instruction limit exceeded");}
            else {assert_eq!(value.unwrap().value,expected);}
        }
    }}
}

#[test]
fn scalar_promotion_widths_copy_directions_and_entry_zero() {
    for size in [1usize,2,4,8,16] {for both in [false,true] {
        let value=0xfedcba98765432100123456789abcdefu128;
        let mask=if size==16 {u128::MAX}else{(1u128<<(size*8))-1};
        let p=program(function(vec![
            Op::Imm{dst:0,value},Op::Local{dst:1,offset:16},Op::Store{address:1,src:0,size:size as u8},
            Op::Local{dst:2,offset:32},Op::Copy{dst:2,src:1,size},
            Op::Local{dst:3,offset:16},Op::Copy{dst:3,src:2,size},Op::Copy{dst:3,src:3,size},
            Op::Load{dst:4,address:3,size:size as u8},Op::Local{dst:5,offset:0},Op::Store{address:5,src:4,size:16},Op::Return,
        ],6));
        let mut slots=vec![Slot{offset:16,size}];if both{slots.push(Slot{offset:32,size});}
        let (out,r)=transformed(&p,&slots);assert_eq!(r.slots,1+usize::from(both));assert!(r.removed_addresses>=2);
        check(&p,&[],value&mask);check(&out,&[],value&mask);
        let zero=program(function(vec![Op::Local{dst:0,offset:16},Op::Load{dst:1,address:0,size:size as u8},Op::Local{dst:2,offset:0},Op::Store{address:2,src:1,size:16},Op::Return],3));
        let (out,r)=transformed(&zero,&[Slot{offset:16,size}]);assert_eq!(r.slots,1);check(&out,&[],0);
    }}
}

#[test]
fn scalar_promotion_backedge_to_original_entry_keeps_carried_values() {
    let p=program(function(vec![
        Op::Local{dst:0,offset:16},Op::Load{dst:1,address:0,size:8},Op::Imm{dst:4,value:1},
        Op::Binary{dst:2,overflow:3,op:Binary::Add,a:1,b:4,bits:64,signed:false},Op::Store{address:0,src:2,size:8},
        Op::Local{dst:5,offset:24},Op::Load{dst:6,address:5,size:8},
        Op::Binary{dst:7,overflow:3,op:Binary::Add,a:6,b:2,bits:64,signed:false},Op::Store{address:5,src:7,size:8},
        Op::Imm{dst:8,value:10},Op::Binary{dst:9,overflow:3,op:Binary::Lt,a:2,b:8,bits:64,signed:false},
        Op::Switch{value:9,cases:vec![(1,0)],otherwise:12},
        Op::Local{dst:10,offset:0},Op::Local{dst:11,offset:24},Op::Copy{dst:10,src:11,size:8},Op::Return,
    ],12));
    let (out,r)=transformed(&p,&[Slot{offset:16,size:8},Slot{offset:24,size:8}]);assert_eq!(r.slots,2);
    assert!(out.functions[0].code.iter().filter_map(|op|if let Op::Switch{cases,..}=op {Some(cases[0].1)}else{None}).all(|target|target>=2));
    check(&p,&[],55);check(&out,&[],55);
}

#[test]
fn scalar_promotion_join_and_calls_preserve_caller_registers() {
    let mut p=program(function(vec![
        Op::Local{dst:0,offset:16},Op::Imm{dst:1,value:123},Op::Store{address:0,src:1,size:8},
        Op::Local{dst:2,offset:32},Op::Call{function:1,args:vec![],destination:2},
        Op::Local{dst:3,offset:48},Op::Load{dst:4,address:3,size:8},Op::Switch{value:4,cases:vec![(0,12)],otherwise:8},
        Op::Local{dst:5,offset:16},Op::Imm{dst:6,value:456},Op::Store{address:5,src:6,size:8},Op::Jump{target:12},
        Op::Local{dst:7,offset:16},Op::Local{dst:8,offset:0},Op::Copy{dst:8,src:7,size:8},Op::Return,
    ],9));
    p.functions[0].args=vec![Slot{offset:48,size:8}];
    let mut callee=function(vec![Op::Imm{dst:0,value:u128::MAX},Op::Imm{dst:8,value:999},Op::Return],9);
    callee.name="callee".into();callee.result=Slot{offset:0,size:0};p.functions.push(callee);
    let (out,r)=transformed(&p,&[Slot{offset:16,size:8}]);assert_eq!(r.slots,1);
    for (arg,expected) in [(0,123),(1,456)] {check(&p,&[arg],expected);check(&out,&[arg],expected);}
}

#[test]
fn scalar_promotion_rejects_unproved_address_uses_and_definitions() {
    let prefixes=vec![
        vec![Op::Local{dst:0,offset:16},Op::Load{dst:1,address:0,size:4}],
        vec![Op::Local{dst:0,offset:16},Op::Copy{dst:1,src:0,size:0}],
        vec![Op::Local{dst:0,offset:16},Op::Copy{dst:1,src:0,size:16}],
        vec![Op::Local{dst:0,offset:16},Op::Store{address:0,src:0,size:8}],
        vec![Op::Local{dst:0,offset:16},Op::Binary{dst:1,overflow:2,op:Binary::Add,a:0,b:2,bits:64,signed:false}],
        vec![Op::Local{dst:0,offset:16},Op::Imm{dst:0,value:0},Op::Load{dst:1,address:0,size:8}],
        vec![Op::Jump{target:2},Op::Local{dst:0,offset:16},Op::Load{dst:1,address:0,size:8}],
        vec![Op::Local{dst:0,offset:16},Op::Jump{target:2},Op::Load{dst:1,address:0,size:8}],
        vec![Op::Local{dst:0,offset:16},Op::Call{function:0,args:vec![0],destination:1}],
        vec![Op::Local{dst:0,offset:16},Op::CallIndirect{callee:2,args:vec![],arg_sizes:vec![],destination:0,result_size:8}],
        vec![Op::Local{dst:0,offset:16},Op::CopyDynamic{dst:1,src:0,size:2}],
        vec![Op::Local{dst:0,offset:16},Op::RegisterTlsDestructor{callback:1,argument:0}],
    ];
    for mut code in prefixes {
        code.push(Op::Return);let before=bincode::serialize(&code).unwrap();let mut count=3;
        let r=promote(&mut code,&mut count,&[Slot{offset:16,size:8}]);assert_eq!(r.slots,0);assert_eq!(count,3);assert_eq!(before,bincode::serialize(&code).unwrap());
    }
}

#[test]
fn scalar_promotion_preserves_faults_at_remaining_memory_accesses() {
    for source in [true,false] {
        let p=program(function(vec![Op::Local{dst:0,offset:16},Op::Imm{dst:1,value:1_000_000},
            if source {Op::Copy{dst:0,src:1,size:8}}else{Op::Copy{dst:1,src:0,size:8}},Op::Return],2));
        let (out,r)=transformed(&p,&[Slot{offset:16,size:8}]);assert_eq!(r.slots,1);
        for engine in engines() {
            let old=execute_with_engine(&p,&[],Limits::default(),engine).unwrap_err();
            let new=execute_with_engine(&out,&[],Limits::default(),engine).unwrap_err();assert_eq!(old,new);assert!(new.contains("memory"));
        }
    }
}
