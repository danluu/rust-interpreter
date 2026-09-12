use super::*;
use crate::{Engine,Limits,Slot,Unary};
fn program(code:Vec<Op>)->Program {
    Program{version:crate::VERSION,target:"aarch64-apple-darwin".into(),entry:0,data:vec![0;32],statics:vec![],thread_locals:vec![],functions:vec![
        Function{name:"root".into(),frame_size:512,frame_align:16,registers:64,args:vec![Slot{offset:16,size:8}],result:Slot{offset:0,size:16},code}
    ]}
}
fn finish(src:u32)->Vec<Op> {vec![Op::Local{dst:0,offset:0},Op::Store{address:0,src,size:16},Op::Return]}
fn run(p:&Program,args:&[u128],engine:Engine,limits:Limits)->Result<(u128,u64,usize),String> {
    crate::execute_with_engine(p,args,limits,engine).map(|e|(e.value,e.instructions,e.peak_memory))
}
fn qualify(p:&Program,args:&[u128])->Program {
    let (mut q,r)=fold(p.clone()).unwrap();assert!(r["functions"].as_array().unwrap().iter().any(|f|f["declined"]==false));
    crate::optimize_control_flow(&mut q).unwrap();
    let before=run(p,args,Engine::Interpreter,Limits::default());let after=run(&q,args,Engine::Interpreter,Limits::default());
    let observable=|r:&Result<(u128,u64,usize),String>|r.as_ref().map(|&(v,_,m)|(v,m)).map_err(|e|e.as_str().to_owned());
    if observable(&before)!=observable(&after) {
        let dir=std::env::temp_dir().join(format!("rust-interp-constant-fold-failure-{}-{}",std::process::id(),std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_nanos()));
        std::fs::create_dir(&dir).unwrap();std::fs::write(dir.join("original.rbc"),bincode::serialize(p).unwrap()).unwrap();
        std::fs::write(dir.join("folded.rbc"),bincode::serialize(&q).unwrap()).unwrap();std::fs::write(dir.join("arguments.txt"),format!("{args:?}")).unwrap();
        panic!("original {before:?} folded {after:?}; artifacts at {dir:?}");
    }
    // Pure-definition removal can make a region too short for native emission.
    // Thus the same JIT mode can switch to interpreter fallback and use its
    // existing range-fault wording. Only these two messages form one category.
    let fault_class=|r:Result<(u128,usize),String>|r.map_err(|e|match e.as_str() {
        "invalid guest memory access"|"JIT guest memory access failed"=>"guest memory range fault".into(),_=>e,
    });
    for resumable in [false,true] {for persistent in [false,true] {
        let limits=Limits{jit_resumable_calls:resumable,jit_persistent_registers:persistent,..Limits::default()};
        let original=run(p,args,Engine::Jit,limits.clone());let folded=run(&q,args,Engine::Jit,limits);
        assert_eq!(fault_class(observable(&original)),fault_class(observable(&folded)));
    }}
    for artifact in [p,&q] {
        let reference=run(artifact,args,Engine::Interpreter,Limits::default());
        let n=reference.as_ref().map_or(50,|e|e.1);
        for resumable in [false,true] {for persistent in [false,true] {for capacity in [0,16*1024*1024] {
            for budget in [0,1,n.saturating_sub(1),n,n+1] {
                let limits=Limits{instructions:budget,..Limits::default()};
                let expected=run(artifact,args,Engine::Interpreter,limits.clone());
                let actual=run(artifact,args,Engine::Jit,Limits{jit_resumable_calls:resumable,jit_persistent_registers:persistent,jit_code_bytes:capacity,..limits});
                // Ordinary native regions already use a distinct range-fault
                // message. Keep all other messages and all budget failures exact.
                let normalize=|r:Result<(u128,u64,usize),String>|r.map_err(|e|match e.as_str() {
                    "invalid guest memory access"|"JIT guest memory access failed"=>"guest memory range fault".into(),_=>e,
                });
                assert_eq!(normalize(actual),normalize(expected),"resumable={resumable} persistent={persistent} capacity={capacity} budget={budget}");
            }
        }}}
    }
    q
}
#[test]
fn constants_cross_diamonds_but_conflicting_values_and_loop_updates_do_not() {
    let code=vec![Op::Local{dst:0,offset:16},Op::Load{dst:1,address:0,size:8},
        Op::Switch{value:1,cases:vec![(0,3)],otherwise:7},
        Op::Local{dst:2,offset:32},Op::Imm{dst:3,value:7},Op::Store{address:2,src:3,size:8},Op::Jump{target:11},
        Op::Local{dst:2,offset:32},Op::Imm{dst:3,value:9},Op::Store{address:2,src:3,size:8},Op::Jump{target:11},
        Op::Local{dst:2,offset:32},Op::Load{dst:4,address:2,size:8},Op::Imm{dst:5,value:1},
        Op::Binary{dst:4,overflow:6,op:Binary::Add,a:4,b:5,bits:64,signed:false},
        Op::Imm{dst:7,value:12},Op::Binary{dst:8,overflow:9,op:Binary::Lt,a:4,b:7,bits:64,signed:false},
        Op::Switch{value:8,cases:vec![(1,14)],otherwise:18}];
    let mut p=program(code);p.functions[0].code.extend(finish(4));
    for arg in [0,1,100] {let q=qualify(&p,&[arg]);assert!(q.functions[0].code.iter().any(|op|matches!(op,Op::Load{..})));}
    // Equal writes on both sides are constant at the join, unlike the variant above.
    p.functions[0].code[8]=Op::Imm{dst:3,value:7};qualify(&p,&[1]);
}
#[test]
fn partial_overlap_copy_fill_and_local_pointer_arithmetic_keep_exact_bytes() {
    let mut p=program(vec![Op::Local{dst:0,offset:32},Op::Imm{dst:1,value:0x0807060504030201},Op::Store{address:0,src:1,size:8},
        Op::Imm{dst:2,value:4},Op::Binary{dst:3,overflow:4,op:Binary::Add,a:0,b:2,bits:64,signed:false},
        Op::Copy{dst:3,src:0,size:8},Op::Load{dst:5,address:0,size:8},
        Op::Imm{dst:6,value:0xff},Op::Imm{dst:7,value:2},Op::FillBytes{address:3,value:6,size:7},
        Op::Load{dst:8,address:0,size:8},Op::Binary{dst:9,overflow:10,op:Binary::Xor,a:5,b:8,bits:64,signed:false}]);
    p.functions[0].code.extend(finish(9));let q=qualify(&p,&[0]);
    assert!(q.functions[0].code.len()<p.functions[0].code.len());
    // Unknown address writes may alias the previously known buffer.
    p.functions[0].code.insert(10,Op::Local{dst:11,offset:16});
    p.functions[0].code.insert(11,Op::Load{dst:12,address:11,size:8});
    p.functions[0].code.insert(12,Op::Store{address:12,src:6,size:1});
    qualify(&p,&[64]);
}
#[test]
fn calls_clobber_local_bytes_while_value_registers_survive() {
    let mut p=program(vec![Op::Local{dst:0,offset:32},Op::Imm{dst:1,value:7},Op::Store{address:0,src:1,size:8},
        Op::Local{dst:2,offset:48},Op::Store{address:2,src:0,size:8},
        Op::Call{function:1,args:vec![2],destination:0},Op::Load{dst:3,address:0,size:8},
        Op::Binary{dst:4,overflow:5,op:Binary::Add,a:1,b:3,bits:64,signed:false}]);
    p.functions[0].code.extend(finish(4));
    p.functions.push(Function{name:"mutate".into(),frame_size:16,frame_align:16,registers:4,args:vec![Slot{offset:0,size:8}],result:Slot{offset:0,size:0},
        code:vec![Op::Local{dst:0,offset:0},Op::Load{dst:1,address:0,size:8},Op::Imm{dst:2,value:11},Op::Store{address:1,src:2,size:8},Op::Return]});
    qualify(&p,&[0]);
}
#[test]
fn generated_wide_integer_and_alias_cases_match_both_engines() {
    let mut seed=0x13579bdf2468ace0u64;
    for case in 0..32 {
        let mut next=||{seed^=seed<<13;seed^=seed>>7;seed^=seed<<17;seed};
        let mut code=vec![Op::Local{dst:0,offset:64},Op::Imm{dst:1,value:0}];
        for index in 0..8 {
            let bits=[8,16,32,64,128][(next()%5) as usize];
            let a=((next() as u128)<<64)|(next() as u128);let b=((next() as u128)<<64)|(next() as u128);
            let op=[Binary::Add,Binary::Sub,Binary::Mul,Binary::And,Binary::Or,Binary::Xor,Binary::Shl,Binary::Shr][(next()%8) as usize];
            code.extend([Op::Imm{dst:2,value:a},Op::Imm{dst:3,value:b},
                Op::Binary{dst:2,overflow:if index%3==0 {2} else {3},op,a:2,b:3,bits,signed:case%2==0},
                Op::Store{address:0,src:2,size:16},Op::Load{dst:4,address:0,size:16},
                Op::Unary{dst:4,op:Unary::SwapBytes,src:4,bits:128},
                Op::Binary{dst:1,overflow:5,op:Binary::Xor,a:1,b:4,bits:128,signed:false}]);
        }
        code.extend(finish(1));qualify(&program(code),&[case]);
    }
}
#[test]
fn unknown_and_known_faults_keep_messages_and_order() {
    for fault in [Op::Binary{dst:2,overflow:3,op:Binary::Div,a:0,b:1,bits:64,signed:false},
        Op::Load{dst:2,address:0,size:8},Op::Assert{value:1,expected:true,message:"first fault".into()}] {
        let mut code=vec![Op::Imm{dst:0,value:123456789},Op::Imm{dst:1,value:0},fault,
            Op::Trap{message:"later fault".into()}];
        qualify(&program(code.clone()),&[0]);
        code[0]=Op::Local{dst:0,offset:16};code.insert(1,Op::Load{dst:0,address:0,size:8});qualify(&program(code),&[123456789]);
    }
}
#[test]
fn joins_are_certified_and_initial_zero_uses_are_not_invented_constants() {
    let mut code=vec![Op::Imm{dst:0,value:1},Op::Switch{value:31,cases:vec![(0,2)],otherwise:4},
        Op::Imm{dst:1,value:7},Op::Jump{target:5},Op::Imm{dst:1,value:11}];code.extend(finish(1));
    let p=program(code);let q=qualify(&p,&[0]);assert!(q.functions[0].code.iter().any(|op|matches!(op,Op::Switch{value:31,..})));
    let f=&p.functions[0];let blocks=blocks(f).unwrap();let mut global=32_000_000;let mut meter=Meter{used:0,global:&mut global};
    let states=solve(&p,f,&blocks,&mut meter).unwrap();assert!(states.last().unwrap().as_ref().unwrap().get(1).is_none());
}
#[test]
fn bounds_decline_complete_functions_without_partial_changes() {
    let mut p=program(vec![Op::Return]);p.functions[0].registers=8193;
    let bytes=bincode::serialize(&p).unwrap();let (q,r)=fold(p).unwrap();assert_eq!(bincode::serialize(&q).unwrap(),bytes);assert_eq!(r["functions"][0]["declined"],true);
    let p=program(vec![Op::Return;4097]);let bytes=bincode::serialize(&p).unwrap();assert_eq!(bincode::serialize(&fold(p).unwrap().0).unwrap(),bytes);
    let p=program(vec![Op::Imm{dst:0,value:1},Op::Return]);let f=&p.functions[0];let mut global=0;let mut meter=Meter{used:0,global:&mut global};assert!(function(&p,f,&mut meter).is_none());
}
