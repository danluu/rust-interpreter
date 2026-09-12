use super::*;
use crate::{Binary,Engine,Limits,Slot};

fn program(code:Vec<Op>)->Program {
    Program{version:crate::VERSION,target:"aarch64-apple-darwin".into(),entry:0,data:vec![0;32],statics:vec![],thread_locals:vec![],functions:vec![
        Function{name:"root".into(),frame_size:64,frame_align:16,registers:16,args:vec![Slot{offset:16,size:8}],result:Slot{offset:0,size:8},code}
    ]}
}
fn finish(value:u128)->Vec<Op> {vec![Op::Local{dst:10,offset:0},Op::Imm{dst:11,value},Op::Store{address:10,src:11,size:8},Op::Return]}
fn returned(register:u32)->Vec<Op> {vec![Op::Local{dst:10,offset:0},Op::Store{address:10,src:register,size:8},Op::Return]}
fn checked(p:&Program,args:&[u128],removes:bool)->Program {
    let mut q=p.clone();let r=optimize(p,&mut q.functions[0],&[],&mut 8_000_000,&mut 8_000_000);
    assert_eq!(r.applied,removes,"{}",serde_json::to_string(&r).unwrap());crate::validate(&q).unwrap();
    let mut same=p.clone();same.functions[0].code=q.functions[0].code.clone();
    assert_eq!(bincode::serialize(&same).unwrap(),bincode::serialize(&q).unwrap());
    for &arg in args {
        let observe=|p:&Program|crate::execute_with_engine(p,&[arg],Limits::default(),Engine::Interpreter).map(|r|(r.value,r.peak_memory));
        assert_eq!(observe(p),observe(&q));
        for artifact in [p,&q] {
            let outcome=crate::execute_with_engine(artifact,&[arg],Limits::default(),Engine::Interpreter);
            let n=outcome.as_ref().map_or(100,|r|r.instructions);
            for resumable in [false,true] {for persistent in [false,true] {for capacity in [0,16*1024*1024] {
                for budget in [0,1,n.saturating_sub(1),n,n+1] {
                    let run=|engine| {
                        let limits=Limits{instructions:budget,jit_resumable_calls:engine==Engine::Jit&&resumable,
                            jit_persistent_registers:engine==Engine::Jit&&persistent,jit_code_bytes:capacity,..Limits::default()};
                        crate::execute_with_engine(artifact,&[arg],limits,engine).map(|r|(r.value,r.instructions,r.peak_memory)).map_err(|e|match e.as_str(){
                            "invalid guest memory access"|"JIT guest memory access failed"=>"guest memory range fault".into(),_=>e})
                    };
                    assert_eq!(run(Engine::Jit),run(Engine::Interpreter),"budget={budget} resumable={resumable} persistent={persistent} capacity={capacity}");
                }
            }}}
        }
    }
    q
}

#[test]
fn unobserved_valid_local_and_immutable_copies_and_clears_can_disappear() {
    let mut p=program(vec![Op::Local{dst:0,offset:32},Op::Local{dst:1,offset:48},Op::Imm{dst:2,value:0xaa},Op::Imm{dst:3,value:8},
        Op::FillBytes{address:0,value:2,size:3},Op::Copy{dst:1,src:0,size:8},Op::Imm{dst:4,value:1},
        Op::CopyDynamic{dst:1,src:4,size:3}]);
    p.functions[0].code.extend(finish(77));let q=checked(&p,&[0],true);
    assert!(q.functions[0].code.iter().all(|op|!matches!(op,Op::FillBytes{..}|Op::Copy{..}|Op::CopyDynamic{..})));
}

#[test]
fn partial_overwrite_and_overlapping_copy_preserve_snapshot_bytes() {
    let mut p=program(vec![Op::Local{dst:0,offset:0},Op::Imm{dst:1,value:0x0807060504030201},Op::Store{address:0,src:1,size:8},
        Op::Local{dst:2,offset:2},Op::Imm{dst:3,value:0xffffffff},Op::Store{address:2,src:3,size:4},Op::Return]);
    checked(&p,&[0],false);
    p.functions[0].code=vec![Op::Local{dst:0,offset:32},Op::Imm{dst:1,value:0x0807060504030201},Op::Store{address:0,src:1,size:8},
        Op::Local{dst:2,offset:34},Op::Copy{dst:2,src:0,size:8},Op::Load{dst:3,address:2,size:8}];
    p.functions[0].code.extend(returned(3));checked(&p,&[0],false);
}

#[test]
fn joins_preserve_a_write_read_on_either_branch() {
    let mut p=program(vec![Op::Local{dst:0,offset:32},Op::Imm{dst:1,value:7},Op::Store{address:0,src:1,size:8},
        Op::Local{dst:2,offset:16},Op::Load{dst:3,address:2,size:8},Op::Switch{value:3,cases:vec![(0,6)],otherwise:9},
        Op::Local{dst:4,offset:32},Op::Load{dst:5,address:4,size:8},Op::Jump{target:10},Op::Imm{dst:5,value:9}]);
    p.functions[0].code.extend(returned(5));checked(&p,&[0,1],false);
    // Both successors now overwrite the buffer before a shared read.
    p.functions[0].code=vec![Op::Local{dst:0,offset:32},Op::Imm{dst:1,value:7},Op::Store{address:0,src:1,size:8},
        Op::Local{dst:2,offset:16},Op::Load{dst:3,address:2,size:8},Op::Switch{value:3,cases:vec![(0,6)],otherwise:10},
        Op::Local{dst:4,offset:32},Op::Imm{dst:5,value:11},Op::Store{address:4,src:5,size:8},Op::Jump{target:13},
        Op::Local{dst:4,offset:32},Op::Imm{dst:5,value:13},Op::Store{address:4,src:5,size:8},
        Op::Local{dst:4,offset:32},Op::Load{dst:5,address:4,size:8}];
    p.functions[0].code.extend(returned(5));checked(&p,&[0,1],true);
}

#[test]
fn loop_carried_frame_bytes_remain_live() {
    let mut p=program(vec![Op::Local{dst:0,offset:32},Op::Imm{dst:1,value:0},Op::Store{address:0,src:1,size:8},
        Op::Local{dst:0,offset:32},Op::Load{dst:2,address:0,size:8},Op::Imm{dst:3,value:1},
        Op::Binary{dst:2,overflow:4,op:Binary::Add,a:2,b:3,bits:64,signed:false},Op::Store{address:0,src:2,size:8},
        Op::Imm{dst:5,value:4},Op::Binary{dst:6,overflow:7,op:Binary::Lt,a:2,b:5,bits:64,signed:false},
        Op::Switch{value:6,cases:vec![(1,3)],otherwise:11},Op::Local{dst:0,offset:32},Op::Load{dst:2,address:0,size:8}]);
    p.functions[0].code.extend(returned(2));checked(&p,&[0],false);
}

#[test]
fn unknown_alias_reads_keep_prior_local_writes_and_null_faults() {
    let mut p=program(vec![Op::Local{dst:0,offset:32},Op::Imm{dst:1,value:7},Op::Store{address:0,src:1,size:8},
        Op::Local{dst:2,offset:16},Op::Load{dst:3,address:2,size:8},Op::Imm{dst:4,value:0},
        Op::Select{dst:5,condition:3,yes:0,no:4},Op::Load{dst:6,address:5,size:8}]);
    p.functions[0].code.extend(returned(6));checked(&p,&[0,1],false);
}

#[test]
fn invalid_copy_sources_and_out_of_frame_writes_keep_their_faults() {
    for value in [0,31,32,u64::MAX as u128] {
        let mut p=program(vec![Op::Local{dst:0,offset:32},Op::Imm{dst:1,value},Op::Copy{dst:0,src:1,size:8}]);
        p.functions[0].code.extend(finish(99));checked(&p,&[0],false);
    }
    let mut p=program(vec![Op::Local{dst:0,offset:63},Op::Imm{dst:1,value:7},Op::Store{address:0,src:1,size:8}]);
    p.functions[0].code.extend(finish(99));checked(&p,&[0],false);
    let mut p=program(vec![Op::Local{dst:0,offset:32},Op::Local{dst:1,offset:16},Op::Load{dst:2,address:1,size:8},
        Op::Imm{dst:3,value:0},Op::FillBytes{address:0,value:3,size:2}]);
    p.functions[0].code.extend(finish(99));checked(&p,&[0,8,64],false);
}

#[test]
fn callees_observing_the_frame_keep_earlier_writes() {
    let mut p=program(vec![Op::Local{dst:0,offset:32},Op::Imm{dst:1,value:7},Op::Store{address:0,src:1,size:8},
        Op::Local{dst:2,offset:40},Op::Store{address:2,src:0,size:8},Op::Local{dst:3,offset:0},
        Op::Call{function:1,args:vec![2],destination:3},Op::Return]);
    p.functions.push(Function{name:"read_caller".into(),frame_size:16,frame_align:8,registers:4,args:vec![Slot{offset:0,size:8}],result:Slot{offset:8,size:8},
        code:vec![Op::Local{dst:0,offset:0},Op::Load{dst:1,address:0,size:8},Op::Load{dst:2,address:1,size:8},
            Op::Local{dst:3,offset:8},Op::Store{address:3,src:2,size:8},Op::Return]});
    checked(&p,&[0],false);
}

#[test]
fn exhausted_work_and_large_frames_decline_without_partial_changes() {
    let mut p=program(vec![Op::Local{dst:0,offset:32},Op::Imm{dst:1,value:7},Op::Store{address:0,src:1,size:8}]);
    p.functions[0].code.extend(finish(5));
    for (facts,live) in [(0,8_000_000),(8_000_000,0),(1,1)] {
        let mut f=p.functions[0].clone();let r=optimize(&p,&mut f,&[],&mut {facts},&mut {live});
        assert!(r.decline.is_some()&&!r.applied);assert_eq!(bincode::serialize(&f).unwrap(),bincode::serialize(&p.functions[0]).unwrap());
    }
    p.functions[0].frame_size=4097;let mut f=p.functions[0].clone();let r=optimize(&p,&mut f,&[],&mut 8_000_000,&mut 8_000_000);
    assert_eq!(r.decline,Some("shape bound"));assert_eq!(bincode::serialize(&f).unwrap(),bincode::serialize(&p.functions[0]).unwrap());
}
