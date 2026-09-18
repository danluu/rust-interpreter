//! Bounded structural census only: no scalar graph, native code or runtime policy.
use super::*;
use crate::scalar_ir;
use serde_json::json;
use std::collections::BTreeSet;

#[derive(Clone,Debug,Serialize)]
struct Candidate {depth:usize,expanded_operations:usize,expanded_frames:usize,expanded_registers:usize,calls:usize}
#[derive(Serialize)]
struct Row {function:usize,name:String,function_sha256:String,candidate:Option<Candidate>,decline:Option<&'static str>}

fn scalar_opcode(op:&Op)->bool {
    matches!(op,Op::Imm{..}|Op::Local{..}|Op::Load{..}|Op::Store{..}|Op::Copy{..}
        |Op::CopyDynamic{..}|Op::FillBytes{..}|Op::Binary{..}|Op::Unary{..}|Op::Cast{..}|Op::Select{..}
        |Op::Jump{..}|Op::Switch{..}|Op::Assert{..}|Op::Trap{..}|Op::Return|Op::Call{..})
}
fn assess(p:&Program,id:usize,accepted:&[bool],rows:&[Option<Candidate>],remaining:&mut usize)->Result<Candidate,&'static str> {
    let f=&p.functions[id];
    if f.code.is_empty() || f.code.len()>512 || f.frame_size>512 || f.registers>512 {return Err("small_shape_limit");}
    if f.args.len()>64 || f.args.iter().chain([&f.result]).any(|s|!matches!(s.size,0|1|2|4|8|16)) {return Err("boundary_width");}
    if f.code.iter().any(|op|!scalar_opcode(op)) {return Err("scalar_opcode");}
    let mut candidate=Candidate{depth:1,expanded_operations:f.code.len(),expanded_frames:f.frame_size.max(1),expanded_registers:f.registers,calls:0};
    for op in &f.code {
        if let Op::Call{function,..}=op {
            let c=rows[*function].as_ref().ok_or("callee_declined")?;
            candidate.depth=candidate.depth.max(c.depth+1);
            candidate.expanded_operations+=c.expanded_operations;
            candidate.expanded_frames+=c.expanded_frames;
            candidate.expanded_registers+=c.expanded_registers;
            candidate.calls+=c.calls+1;
            if candidate.depth>4 || candidate.expanded_operations>2048 || candidate.expanded_frames>4096
                || candidate.expanded_registers>2048 {return Err("expanded_shape_limit");}
        }
    }
    if candidate.calls==0 {
        let memory=memory_plan(p,id,remaining);
        if !memory.eligible {return Err(memory.decline.unwrap().reason);}
        let graph=scalar_ir::lower(f,&memory,250_000)?;
        // Offline words only. Current leaf emitability is a prerequisite for
        // future parent work; parent graphs themselves are not implemented.
        scalar_ir::native_leaf::emit_call(&graph,false)?;
        return Ok(candidate);
    }
    for mode in [Mode::Initialized,Mode::Confined] {
        let proof=analyze_budgeted(p,id,accepted,mode,remaining);
        if !proof.eligible {return Err(proof.decline.unwrap().reason);}
    }
    // Use the same bounded typed CFG builder, then independently require a DAG.
    let mut analysis=Analysis{program:p,confined:accepted,mode:Mode::Confined,work:0,max_work:MAX_WORK.min(*remaining),pc:0};
    let blocks=analysis.blocks(f).map_err(|d|d.reason);
    *remaining=remaining.saturating_sub(analysis.work);
    let blocks=blocks?;
    let mut reachable=BTreeSet::from([0]);let mut todo=vec![0];
    while let Some(b)=todo.pop() {for &s in &blocks[b].successors {if reachable.insert(s) {todo.push(s);}}}
    let mut indegree=vec![0;blocks.len()];
    for &b in &reachable {for &s in &blocks[b].successors {indegree[s]+=1;}}
    let mut ready:VecDeque<_>=reachable.iter().copied().filter(|&b|indegree[b]==0).collect();let mut visited=0;
    while let Some(b)=ready.pop_front() {visited+=1;for &s in &blocks[b].successors {indegree[s]-=1;if indegree[s]==0 {ready.push_back(s);}}}
    if visited!=reachable.len() {return Err("scalar_cycle");}
    Ok(candidate)
}
fn census(p:&Program,remaining:&mut usize)->Vec<Row> {
    assert!(p.functions.len()<=65_536 && p.functions.iter().map(|f|f.code.len()).sum::<usize>()<=2_000_000);
    let n=p.functions.len();let mut dependents=vec![vec![];n];let mut pending=vec![0;n];
    for (id,f) in p.functions.iter().enumerate() {
        let deps:BTreeSet<_>=f.code.iter().filter_map(|op|if let Op::Call{function,..}=op {Some(*function)} else {None}).collect();
        pending[id]=deps.len();for dep in deps {dependents[dep].push(id);}
    }
    let mut ready:VecDeque<_>=(0..n).filter(|&id|pending[id]==0).collect();
    let mut accepted=vec![false;n];let mut candidates=vec![None;n];let mut declines=vec![Some("call_cycle_or_dependency");n];
    while let Some(id)=ready.pop_front() {
        match assess(p,id,&accepted,&candidates,remaining) {
            Ok(c)=>{accepted[id]=true;candidates[id]=Some(c);declines[id]=None;}
            Err(reason)=>declines[id]=Some(reason),
        }
        for &parent in &dependents[id] {pending[parent]-=1;if pending[parent]==0 {ready.push_back(parent);}}
    }
    candidates.into_iter().zip(declines).enumerate().map(|(function,(candidate,decline))|
        Row{function,name:p.functions[function].name.clone(),function_sha256:{use sha2::{Digest,Sha256};format!("{:x}",Sha256::digest(bincode::serialize(&p.functions[function]).unwrap()))},candidate,decline}).collect()
}

#[test]
#[ignore="Requires pinned original artifact and new output file"]
fn observe_saved_scalar_chains() {
    use sha2::{Digest,Sha256};
    let bytes=std::fs::read(std::env::var("CHAIN_ARTIFACT").unwrap()).unwrap();assert!(bytes.len()<=128*1024*1024);
    let hash=format!("{:x}",Sha256::digest(&bytes));assert_eq!(hash,std::env::var("CHAIN_ARTIFACT_SHA256").unwrap());
    let p:Program=bincode::deserialize(&bytes).unwrap();crate::validate(&p).unwrap();
    let mut remaining=MAX_GLOBAL_WORK;let rows=census(&p,&mut remaining);assert!(remaining>0);
    let calls:Vec<_>=p.functions.iter().enumerate().flat_map(|(id,f)|f.code.iter().enumerate().filter_map(move |(pc,op)|
        if let Op::Call{function,..}=op {Some(json!({"caller":id,"pc":pc,"callee":function}))} else {None})).collect();
    let file=std::fs::OpenOptions::new().write(true).create_new(true).open(std::env::var("CHAIN_OUTPUT").unwrap()).unwrap();
    serde_json::to_writer(file,&json!({"status":"passed","artifact_sha256":hash,"rows":rows,"calls":calls,
        "memory_work_remaining":remaining,"memory_work_used":MAX_GLOBAL_WORK-remaining,
        "original_project_guest_commands":0,"executable_code_publications":0,"production_policy_changed":false,
        "scope":"Structural initialized/confined direct-call DAGs only. Parent scalar graphs, virtual-frame address identity, resource peaks, original-PC accounting and transactional replay are not implemented or qualified."})).unwrap();
}

#[cfg(test)]
mod controls {
    use super::*;
    use crate::{Slot,VERSION};
    fn leaf()->Function {Function{name:"identity".into(),frame_size:16,frame_align:8,registers:3,
        args:vec![Slot{offset:0,size:8}],result:Slot{offset:8,size:8},
        code:vec![Op::Local{dst:0,offset:0},Op::Local{dst:1,offset:8},Op::Copy{dst:1,src:0,size:8},Op::Return]}}
    fn wrapper(child:usize)->Function {let mut f=leaf();f.name="wrapper".into();f.code[2]=Op::Call{function:child,args:vec![0],destination:1};f}
    fn program(functions:Vec<Function>)->Program {Program{version:VERSION,target:"aarch64-apple-darwin".into(),entry:0,functions,data:vec![0;16],statics:vec![],thread_locals:vec![]}}
    fn check(p:&Program)->Vec<Row> {crate::validate(p).unwrap();census(p,&mut MAX_GLOBAL_WORK.clone())}
    #[test]
    fn local_argument_result_chains_preserve_order_and_reference_values() {
        let p=program(vec![wrapper(1),wrapper(2),leaf()]);let rows=check(&p);
        assert!(rows.iter().all(|r|r.candidate.is_some()));
        let c=rows[0].candidate.as_ref().unwrap();assert_eq!((c.depth,c.calls,c.expanded_operations),(3,2,12));
        for value in [0,1,u64::MAX as u128,1u128<<32,1u128<<63] {
            let result=crate::execute_with_engine(&p,&[value],crate::Limits::default(),crate::Engine::Interpreter).unwrap();
            assert_eq!(result.value,value as u64 as u128);assert_eq!(result.instructions,12);
        }
        for value in [1u128<<80,u128::MAX] {
            let error=crate::execute_with_engine(&p,&[value],crate::Limits::default(),crate::Engine::Interpreter).unwrap_err();
            assert_eq!(error,"entry argument exceeds its integer width");
        }
        let mut p=p;p.functions[0].code.insert(3,Op::Call{function:2,args:vec![1],destination:1});
        let rows=check(&p);let c=rows[0].candidate.as_ref().unwrap();
        assert_eq!((c.depth,c.calls,c.expanded_operations),(3,3,17));
    }
    #[test]
    fn missing_initialization_and_external_reads_do_not_become_pure_calls() {
        let mut p=program(vec![wrapper(1),leaf()]);p.functions[0].args.clear();
        assert_eq!(check(&p)[0].decline,Some("local_read_before_write"));
        let mut p=program(vec![wrapper(1),leaf()]);p.functions[1].code.insert(2,Op::Load{dst:2,address:0,size:8});
        p.functions[1].code.insert(3,Op::Load{dst:2,address:2,size:8});
        let rows=check(&p);assert_eq!(rows[1].decline,Some("unknown_pointer_read"));assert_eq!(rows[0].decline,Some("callee_declined"));
    }
    #[test]
    fn recursion_cfg_cycles_and_resource_bounds_decline() {
        let p=program(vec![wrapper(1),wrapper(0)]);assert!(check(&p).iter().all(|r|r.decline==Some("call_cycle_or_dependency")));
        let mut p=program(vec![wrapper(1),leaf()]);p.functions[0].code[3]=Op::Jump{target:0};assert_eq!(check(&p)[0].decline,Some("scalar_cycle"));
        let p=program(vec![wrapper(1),wrapper(2),wrapper(3),wrapper(4),leaf()]);assert_eq!(check(&p)[0].decline,Some("expanded_shape_limit"));
        assert!(check(&p)[1].candidate.is_some());
        assert!(census(&program(vec![wrapper(1),leaf()]),&mut 0).iter().all(|r|r.candidate.is_none()));
    }
    #[test]
    fn boundary_and_unknown_effects_keep_conservative_admission() {
        let mut p=program(vec![wrapper(1),leaf()]);p.functions[1].args[0].size=3;p.functions[1].result.size=3;
        assert_eq!(check(&p)[1].decline,Some("boundary_width"));
        let mut p=program(vec![wrapper(1),leaf()]);p.functions[1].code.insert(2,Op::CompareBytes{dst:2,left:0,right:1,size:2});
        assert_eq!(check(&p)[1].decline,Some("scalar_opcode"));assert_eq!(check(&p)[0].decline,Some("callee_declined"));
    }
}
