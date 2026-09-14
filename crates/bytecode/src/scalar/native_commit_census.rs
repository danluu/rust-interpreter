//! Read-only census of private Call commit traffic in qualified scalar bodies.
use super::*;
use serde_json::{Value as Json, json};
use sha2::{Digest, Sha256};
use std::collections::VecDeque;

// Conservative structural path lengths: no assertion or branch outcome is
// guessed. A fault-only path contributes no successful Return. Different
// lengths decline a constant even if a path might be infeasible at runtime.
fn successful_steps(plan:&Plan)->Option<(usize,usize)> {
    let n=plan.blocks.len();
    if n==0 || n>512 || plan.effects.len()>512 || plan.reachable.len()!=n {return None;}
    let mut pending=vec![0usize;n];let mut edges=0;
    for (i,b) in plan.blocks.iter().enumerate() {
        if !plan.reachable[i] {continue;}
        if b.start>=b.end || b.end>plan.effects.len() {return None;}
        for &next in &b.successors {
            if next>=n || !plan.reachable[next] {return None;}
            pending[next]+=1;edges+=1;if edges>8192 {return None;}
        }
    }
    let mut queue:VecDeque<_>=(0..n).filter(|&i|plan.reachable[i] && pending[i]==0).collect();
    let mut ranges=vec![None::<(usize,usize)>;n];ranges[0]=Some((0,0));
    let mut result=None::<(usize,usize)>;let mut visited=0;
    while let Some(i)=queue.pop_front() {
        visited+=1;let b=&plan.blocks[i];let (lo,hi)=ranges[i]?;
        let length=b.end-b.start;let (lo,hi)=(lo+length,hi+length);
        if hi>512 {return None;}
        if matches!(plan.effects[b.end-1],Effect::Return(_)) {
            if !b.successors.is_empty() {return None;}
            result=Some(match result {None=>(lo,hi),Some((a,z))=>(a.min(lo),z.max(hi))});
        }
        for &next in &b.successors {
            ranges[next]=Some(match ranges[next] {None=>(lo,hi),Some((a,z))=>(a.min(lo),z.max(hi))});
            pending[next]-=1;if pending[next]==0 {queue.push_back(next);}
        }
    }
    if visited!=plan.reachable.iter().filter(|&&v|v).count() {return None;}
    result
}

#[test]
fn scalar_commit_census_keeps_unequal_returns_traps_and_nonmonotonic_edges() {
    let make=|code:Vec<Op>| {
        let f=Function{name:"commit census control".into(),frame_size:0,frame_align:8,
            registers:2,args:vec![],result:crate::Slot{offset:0,size:0},code};
        let p=crate::Program{version:crate::VERSION,target:"aarch64-apple-darwin".into(),entry:0,
            functions:vec![f],data:vec![],statics:vec![],thread_locals:vec![]};
        crate::validate(&p).unwrap();let m=crate::proof::memory_plan(&p,0,&mut crate::proof::MAX_GLOBAL_WORK.clone());
        lower(&p.functions[0],&m,250_000).unwrap()
    };
    let imm=||Op::Imm{dst:0,value:1};
    let branch=|a,b|Op::Switch{value:0,cases:vec![(0,a)],otherwise:b};
    assert_eq!(successful_steps(&make(vec![Op::Return])),Some((1,1)));
    assert_eq!(successful_steps(&make(vec![imm(),branch(2,3),Op::Return,imm(),Op::Return])),Some((3,4)));
    assert_eq!(successful_steps(&make(vec![imm(),branch(2,4),imm(),Op::Return,imm(),Op::Return])),Some((4,4)));
    let p=make(vec![imm(),branch(2,3),Op::Return,imm(),imm(),Op::Trap{message:"long fault".into()}]);
    assert_eq!(successful_steps(&p),Some((3,3)));assert_eq!(p.maximum_steps,5);
    assert_eq!(successful_steps(&make(vec![Op::Jump{target:3},imm(),Op::Return,Op::Jump{target:1}])),Some((4,4)));
    assert_eq!(successful_steps(&make(vec![Op::Trap{message:"no return".into()}])),None);
    let mut p=make(vec![Op::Return]);p.blocks[0].successors.push(0);assert_eq!(successful_steps(&p),None);
}

#[test]
#[ignore="Requires pinned public artifacts and closed private Call ABI profiles"]
fn observe_original_scalar_commit_traffic() {
    let input:Json=serde_json::from_slice(&std::fs::read(std::env::var("SCALAR_COMMIT_INPUT").unwrap()).unwrap()).unwrap();
    let mut cases=vec![];
    for case in input.as_array().unwrap() {
        let read=|key:&str| {
            let data=std::fs::read(case[key].as_str().unwrap()).unwrap();assert!(data.len()<=128*1024*1024);
            assert_eq!(format!("{:x}",Sha256::digest(&data)),case[format!("{key}_sha256")]);data
        };
        let program:crate::Program=bincode::deserialize(&read("artifact")).unwrap();crate::validate(&program).unwrap();
        let profile:Json=serde_json::from_slice(&read("profile")).unwrap();
        let mapping:Json=serde_json::from_slice(&read("map")).unwrap();let code=read("code");
        assert_eq!(mapping["profiled"],true);assert_eq!(mapping["architecture"],"aarch64");
        let mut work=crate::proof::MAX_GLOBAL_WORK;let mut rows=vec![];
        for (function,f) in program.functions.iter().enumerate() {
            let memory=crate::proof::memory_plan(&program,function,&mut work);
            let ranges:Vec<_>=mapping["ranges"].as_array().unwrap().iter().filter(|r|
                r["kind"]=="scalar_leaf" && r["function"]==function).collect();
            if ranges.is_empty() {continue;}assert_eq!(ranges.len(),1);let range=ranges[0];assert_eq!(range["name"],f.name);
            let plan=lower(f,&memory,250_000).unwrap();let emitted=emit_call(&plan,true).unwrap();
            let bytes:Vec<_>=emitted.words.iter().flat_map(|w|w.to_le_bytes()).collect();
            assert_eq!(bytes,code[range["offset"].as_u64().unwrap() as usize..range["end"].as_u64().unwrap() as usize],"body {function}");
            let observed=&profile["functions"][function];assert_eq!(observed["name"],f.name);
            let hits:Vec<u64>=serde_json::from_value(observed["jit_scalar_hits"].clone()).unwrap();assert_eq!(hits.len(),f.code.len());
            let calls:u64=f.code.iter().zip(&hits).filter(|(op,_)|matches!(op,Op::Return)).map(|(_,h)|*h).sum();
            assert_eq!(hits[0],calls);
            let steps=successful_steps(&plan);let fixed=steps.filter(|(lo,hi)|lo==hi).map(|(lo,_)|lo);
            let total_steps:u64=hits.iter().sum();
            if let Some(steps)=fixed {assert_eq!(total_steps,calls*steps as u64);}
            let blocks:u64=plan.blocks.iter().enumerate().filter(|(i,_)|plan.reachable[*i]).map(|(_,b)| {
                assert!(hits[b.start..b.end].iter().all(|&h|h==hits[b.start]));hits[b.start]
            }).sum();
            rows.push(json!({"function":function,"name":f.name,"successful_calls":calls,"result_bytes":f.result.size,
                "success_step_range":steps,"fixed_success_steps":fixed,"maximum_steps":plan.maximum_steps,
                "successful_steps":total_steps,"successful_blocks":blocks,
                "scalar_body_bytes":bytes.len(),"spill_bytes":emitted.stack_bytes,
                "possible_step_counter_accesses":if fixed.is_some() {calls*2+blocks*2} else {0},
                "possible_zero_result_accesses":if f.result.size==0 {calls*6} else {0}}));
        }
        let expected=mapping["ranges"].as_array().unwrap().iter().filter(|r|r["kind"]=="scalar_leaf").count();
        assert_eq!(rows.len(),expected);cases.push(json!({"index":case["index"],"functions":rows}));
    }
    let output=std::fs::OpenOptions::new().write(true).create_new(true).open(std::env::var("SCALAR_COMMIT_OUTPUT").unwrap()).unwrap();
    serde_json::to_writer(output,&json!({"status":"passed","cases":cases,"guest_commands":0,"executable_code_publications":0,
        "production_runtime_changes":0,"performance_measurement":false,
        "scope":"Conservative structural successful-path counts and original successful scalar Call counts. Step accesses are one initialization store, two accesses per visited block and one caller load. Zero-result accesses are two leaf stores, three caller loads and one destination save. These are overlapping opportunities, not measured hardware accesses or speedups; failed native attempts are excluded."})).unwrap();
}
