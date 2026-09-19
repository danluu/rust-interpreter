//! Offline structural overlap only. No JIT construction or code-cache admission.
use crate::{Function, Op, Program};
use sha2::{Digest, Sha256};
use std::collections::VecDeque;

fn digest(value: &impl serde::Serialize) -> Result<String, String> {
    let bytes = bincode::serialize(value).map_err(|e| e.to_string())?;
    Ok(format!("{:x}", Sha256::digest(bytes)))
}

fn checked(program: &Program) -> Result<(), String> {
    if program.version & crate::PARTIAL_VALIDATION != 0 {
        return Err("cross-edit census requires fully checked artifacts".into());
    }
    crate::validate(program)
}

fn context(program: &Program) -> Result<String, String> {
    let uses_heap = !program.statics.is_empty() || program.functions.iter().flat_map(|f| &f.code).any(|op| {
        matches!(op, Op::Allocate { .. } | Op::Deallocate { .. } | Op::Reallocate { .. }
            | Op::CAllocate { .. } | Op::CReallocate { .. } | Op::CAlignedAllocate { .. }
            | Op::CurrentDirectory { .. })
    });
    digest(&(program.version, &program.target, program.entry, program.functions.len(), uses_heap,
        &program.data, &program.statics, &program.thread_locals))
}

fn compare(previous: &Program, current: &Program) -> Result<serde_json::Value, String> {
    checked(previous)?; checked(current)?;
    let before = previous.functions.iter().map(digest).collect::<Result<Vec<_>,_>>()?;
    let after = current.functions.iter().map(digest).collect::<Result<Vec<_>,_>>()?;
    let same: Vec<_> = after.iter().enumerate().map(|(id, hash)| before.get(id) == Some(hash)).collect();
    let mut direct = same.clone();
    let mut graph = same.clone();
    let mut callers = vec![vec![]; current.functions.len()];
    for (id, f) in current.functions.iter().enumerate() {
        for op in &f.code {
            match op {
                Op::Call { function, .. } => {
                    direct[id] &= same[*function];
                    callers[*function].push(id);
                }
                // This stricter graph count declines unknown indirect callees;
                // it is not a claim that ordinary code needs their bodies.
                Op::CallIndirect { .. } => { direct[id] = false; graph[id] = false; }
                _ => {}
            }
        }
    }
    let mut queue: VecDeque<_> = graph.iter().enumerate().filter_map(|(id,&same)| (!same).then_some(id)).collect();
    while let Some(id) = queue.pop_front() {
        for &caller in &callers[id] {
            if graph[caller] { graph[caller] = false; queue.push_back(caller); }
        }
    }
    let globals_equal = context(previous)? == context(current)?;
    let count = |mask: &[bool]| serde_json::json!({
        "functions": mask.iter().filter(|&&v|v).count(),
        "operations": current.functions.iter().zip(mask).filter(|(_,v)|**v).map(|(f,_)|f.code.len()).sum::<usize>()
    });
    let rows: Vec<_> = current.functions.iter().enumerate().map(|(id,f)| serde_json::json!({
        "function":id, "name":f.name, "operations":f.code.len(), "sha256":after[id],
        "same_function_at_same_id":same[id], "same_function_and_direct_callees":direct[id],
        "same_closed_direct_call_graph":graph[id],
        "global_context_and_graph_equal":globals_equal && graph[id]
    })).collect();
    Ok(serde_json::json!({
        "previous_functions":previous.functions.len(), "current_functions":current.functions.len(),
        "current_operations":current.functions.iter().map(|f|f.code.len()).sum::<usize>(),
        "global_context_equal":globals_equal,
        "same_function_at_same_id":count(&same), "same_function_and_direct_callees":count(&direct),
        "same_closed_direct_call_graph":count(&graph),
        "global_context_and_graph_equal":count(&graph.iter().map(|&v|v && globals_equal).collect::<Vec<_>>()),
        "functions":rows,
        "cache_admission":false, "performance_measurement":false,
        "scope":"Structural overlap over every artifact function; not executed-function coverage, emitted-code equality, a complete cache key or recoverable latency. Runtime options, scalar admission/budgets, assertions and relocation remain separate obligations."
    }))
}

fn function(name: &str, code: Vec<Op>) -> Function {
    Function { name:name.into(), frame_size:16, frame_align:8, registers:2,
        args:vec![], result:crate::Slot{offset:0,size:0}, code }
}
fn fixture() -> Program {
    let call = |id| vec![Op::Call{function:id,args:vec![],destination:0}, Op::Return];
    Program { version:crate::VERSION, target:"aarch64-apple-darwin".into(), entry:0,
        data:vec![], statics:vec![], thread_locals:vec![],
        functions:vec![function("root",call(1)), function("middle",call(2)),
            function("leaf",vec![Op::Imm{dst:0,value:7},Op::Return]), function("unrelated",vec![Op::Return])] }
}

#[test]
fn cross_edit_unchanged_functions_and_context_are_exact() {
    let p=fixture(); let r=compare(&p,&p).unwrap();
    assert_eq!(r["global_context_and_graph_equal"]["functions"],4);
    assert_eq!(r["current_operations"],7);
    assert_eq!(r["cache_admission"],false);
}

#[test]
fn cross_edit_body_and_layout_changes_propagate_beyond_direct_callees() {
    let p=fixture();
    for layout in [false,true] {
        let mut q=p.clone();
        if layout {q.functions[2].frame_size=32;} else {q.functions[2].code[0]=Op::Imm{dst:0,value:8};}
        let r=compare(&p,&q).unwrap();
        assert_eq!(r["same_function_at_same_id"]["functions"],3);
        assert_eq!(r["same_function_and_direct_callees"]["functions"],2);
        assert_eq!(r["same_closed_direct_call_graph"]["functions"],1);
        assert_eq!(r["functions"][3]["same_closed_direct_call_graph"],true);
    }
}

#[test]
fn cross_edit_cycles_terminate_and_propagate_changes() {
    let mut p=fixture();p.functions[2].code=vec![Op::Call{function:0,args:vec![],destination:0},Op::Return];
    assert_eq!(compare(&p,&p).unwrap()["same_closed_direct_call_graph"]["functions"],4);
    let mut q=p.clone();q.functions[1].name.push('!');
    assert_eq!(compare(&p,&q).unwrap()["same_closed_direct_call_graph"]["functions"],1);
}

#[test]
fn cross_edit_ordinal_identity_never_matches_names_alone() {
    let mut p=fixture();p.functions[2].name="duplicate".into();p.functions[3].name="duplicate".into();
    let mut q=p.clone();q.functions.swap(2,3);
    let r=compare(&p,&q).unwrap();
    assert_eq!(r["same_function_at_same_id"]["functions"],2);
    assert_eq!(r["same_closed_direct_call_graph"]["functions"],0);
}

#[test]
fn cross_edit_global_data_target_and_entry_changes_are_separate() {
    let p=fixture();
    for which in 0..5 {
        let mut q=p.clone();
        match which {0=>q.data.push(1),1=>q.target.push('!'),2=>q.entry=3,3=>q.statics=vec![0;16],
            _=>q.functions[3].code=vec![Op::Allocate{dst:0,size:1,align:1,zeroed:true},Op::Return]}
        let r=compare(&p,&q).unwrap();
        assert_eq!(r["same_function_at_same_id"]["functions"],if which==4 {3} else {4});
        assert_eq!(r["global_context_and_graph_equal"]["functions"],0);
    }
}

#[test]
fn cross_edit_partial_invalid_and_indirect_graphs_are_not_admitted() {
    let p=fixture();let mut q=p.clone();q.version |= crate::PARTIAL_VALIDATION;
    assert!(compare(&p,&q).is_err());assert!(compare(&q,&p).is_err());
    q=p.clone();q.functions[2].code=vec![Op::Jump{target:999}];assert!(compare(&p,&q).is_err());
    q=p.clone();q.functions[2].code=vec![Op::CallIndirect{callee:0,args:vec![],arg_sizes:vec![],destination:1,result_size:0},Op::Return];
    let r=compare(&q,&q).unwrap();
    assert_eq!(r["same_function_at_same_id"]["functions"],4);
    assert_eq!(r["same_closed_direct_call_graph"]["functions"],1);
}

#[test]
fn cross_edit_long_chains_use_bounded_iterative_propagation() {
    let mut p=fixture();p.functions.clear();
    for id in 0..4096 {
        let code=if id==4095 {vec![Op::Return]} else {vec![Op::Call{function:id+1,args:vec![],destination:0},Op::Return]};
        p.functions.push(function("chain",code));
    }
    let mut q=p.clone();q.functions[4095].frame_align=16;
    assert_eq!(compare(&p,&q).unwrap()["same_closed_direct_call_graph"]["functions"],0);
}

#[derive(serde::Deserialize)]
struct Input { path:std::path::PathBuf, sha256:String, state:i32 }
fn read(input: &Input) -> Result<Program,String> {
    use bincode::Options;
    let metadata=std::fs::symlink_metadata(&input.path).map_err(|e|e.to_string())?;
    if !metadata.is_file() || metadata.len()>64*1024*1024 {return Err("expected regular artifact at most64MiB".into());}
    let bytes=std::fs::read(&input.path).map_err(|e|e.to_string())?;
    if format!("{:x}",Sha256::digest(&bytes))!=input.sha256 {return Err("artifact identity mismatch".into());}
    let program:Program=bincode::DefaultOptions::new().with_fixint_encoding().with_limit(64*1024*1024)
        .reject_trailing_bytes().deserialize(&bytes).map_err(|e|e.to_string())?;
    checked(&program)?;Ok(program)
}

#[test]
#[ignore = "explicit saved artifact manifest required; no guest execution"]
fn cross_edit_observe_saved_artifact_sequence() {
    use std::io::Write;
    let manifest=std::env::var_os("RUST_INTERP_CROSS_EDIT_INPUTS").expect("manifest path");
    let inputs:Vec<Input>=serde_json::from_slice(&std::fs::read(manifest).unwrap()).unwrap();
    assert_eq!(inputs.iter().map(|i|i.state).collect::<Vec<_>>(),vec![0,-1,1,2,3,4,5,0]);
    let mut previous=read(&inputs[0]).unwrap();let mut comparisons=vec![];
    for pair in inputs.windows(2) {
        let current=read(&pair[1]).unwrap();let mut row=compare(&previous,&current).unwrap();
        row["previous_state"]=pair[0].state.into();row["state"]=pair[1].state.into();
        row["previous_artifact_sha256"]=pair[0].sha256.clone().into();row["artifact_sha256"]=pair[1].sha256.clone().into();
        comparisons.push(row);previous=current;
    }
    let output=std::env::var_os("RUST_INTERP_CROSS_EDIT_OUTPUT").expect("output path");
    let bytes=serde_json::to_vec_pretty(&serde_json::json!({"comparisons":comparisons,
        "guest_commands":0,"executable_code_publications":0,"cache_admission":false})).unwrap();
    assert!(bytes.len()<=64*1024*1024);
    std::fs::OpenOptions::new().write(true).create_new(true).open(output).unwrap().write_all(&bytes).unwrap();
}
