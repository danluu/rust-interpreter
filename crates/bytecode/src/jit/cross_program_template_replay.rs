//! Explicit diagnostic replay of retained artifacts. No native arena or guest.
use super::*;
use bincode::Options;
use serde::Deserialize;
use std::time::Instant;

#[derive(Deserialize)]
struct Artifact {path:String,sha256:String,state:i32}
#[derive(Deserialize)]
struct Observed {function:usize,name:String,operations:usize,sha256:String}
#[derive(Deserialize)]
struct Worker {worker:usize,functions:Vec<Observed>}
#[derive(Deserialize)]
struct Input {artifacts:Vec<Artifact>,workers:Vec<Worker>}

fn read(path:&str,limit:u64)->Vec<u8> {
    use std::io::Read;
    let file=std::fs::File::open(path).unwrap();assert!(file.metadata().unwrap().len()<=limit);
    let mut bytes=vec![];file.take(limit+1).read_to_end(&mut bytes).unwrap();assert!(bytes.len() as u64<=limit);bytes
}
fn digest(bytes:&[u8])->String {format!("{:x}",Sha256::digest(bytes))}
fn program(a:&Artifact)->Program {
    let bytes=read(&a.path,64*1024*1024);assert_eq!(digest(&bytes),a.sha256);
    let p=bincode::DefaultOptions::new().with_fixint_encoding().with_limit(64*1024*1024)
        .reject_trailing_bytes().deserialize(&bytes).unwrap();
    Checked::new(&p).unwrap();p
}
fn owner<'p>(p:&'p Program,worker:&Worker,base:usize)->(Jit<'p>,usize) {
    let mut jit=Jit::new_resumable(p,false,MAX_CODE_BYTES,true).unwrap();jit.enable_scalar_calls();
    // Disable only diagnostic vectors, identically in both owners. These flags
    // are explicit identity inputs. The scalar table here is a modeled table,
    // not a replay of the original runtime's admission order or arena usage.
    jit.observe_guarded_local_retention=false;jit.observe_static_local_facts=false;jit.observe_scalar_copy=false;
    let mut callees=BTreeSet::new();
    for row in &worker.functions {
        if let Some(f)=p.functions.get(row.function) {
            for op in &f.code {if let Op::Call{function,..}=op {callees.insert(*function);}}
        }
    }
    let mut proof_work=crate::proof::MAX_GLOBAL_WORK;let mut scalar_work=128_000_000usize;let mut admitted=0;
    for id in callees {
        let f=&p.functions[id];if f.args.len()>64 {continue;}
        let memory=crate::proof::memory_plan(p,id,&mut proof_work);let limit=scalar_work.min(250_000);
        let lowered=crate::scalar_ir::lower(f,&memory,limit);
        scalar_work=scalar_work.saturating_sub(match &lowered {Ok(p)=>p.work,Err("no_memory_plan")=>0,Err(_)=>limit});
        let Ok(plan)=lowered else {continue;};
        let Ok(emitted)=crate::scalar_ir::native_leaf::emit_call(&plan,false) else {continue;};
        if emitted.words.len()*4>MAX_CODE_BYTES {continue;}
        // A synthetic, never-executed target varies across owners. The existing
        // observer independently repeats proof/lowering and checks code length.
        let target=base.checked_add(id.checked_mul(4096).unwrap()).unwrap();
        assert_eq!(jit.observe_saved_scalar_entry(id,0,emitted.words.len()*4,target),emitted.words);admitted+=1;
    }
    (jit,admitted)
}

#[test]
#[ignore="requires explicitly hash-bound saved artifacts; never executes generated code"]
fn cross_program_template_replay_saved_parser_edits() {
    let input_path=std::env::var("RUST_INTERP_TEMPLATE_REPLAY_INPUT").unwrap();
    let output_path=std::env::var("RUST_INTERP_TEMPLATE_REPLAY_OUTPUT").unwrap();
    let input_bytes=read(&input_path,16*1024*1024);let input:Input=serde_json::from_slice(&input_bytes).unwrap();
    assert_eq!(input.artifacts.iter().map(|a|a.state).collect::<Vec<_>>(),[0,-1,1,2,3,4,5,0]);
    assert_eq!(input.workers.iter().map(|w|w.worker).collect::<Vec<_>>(),[0,1]);
    let p=program(&input.artifacts[0]);let checked=Checked::new(&p).unwrap();
    let emitter:[u8;32]=[29;32];let mut reports=vec![];
    for worker in &input.workers {
        assert!(worker.functions.len()<=16_384);
        let mut prior=None;
        for row in &worker.functions {
            assert!(prior.is_none_or(|old|old<row.function));prior=Some(row.function);
            let f=&p.functions[row.function];assert_eq!(f.name,row.name);assert_eq!(f.code.len(),row.operations);
            assert_eq!(digest(&bincode::serialize(f).unwrap()),row.sha256);
        }
        let (old,old_scalars)=owner(&p,worker,0x123400000000);
        let mut templates=BTreeMap::new();let mut retained=0;let mut declines=vec![];
        for row in &worker.functions {
            let staged=match old.emit_function(&p.functions[row.function],MAX_CODE_BYTES/4) {
                Ok(Some(staged))=>staged,
                Ok(None)|Err(EmitError::Limit(_))=>{declines.push((row.function,"emission"));continue;},
                Err(error)=>panic!("invalid fresh staging for {}: {error:?}",row.function),
            };
            let Some(template)=Template::capture_mode(&checked,&old,row.function,emitter,&staged,MAX_RETAINED-retained,true)
                else {declines.push((row.function,"capture_or_storage"));continue;};
            retained=retained.checked_add(template.charge().unwrap()).unwrap();assert!(retained<=MAX_RETAINED);
            templates.insert(row.function,template);
        }
        assert!(!templates.is_empty());let mut comparisons=vec![];
        for (ordinal,artifact) in input.artifacts.iter().enumerate().skip(1) {
            let q=program(artifact);let current=Checked::new(&q).unwrap();
            let (mut new,new_scalars)=owner(&q,worker,0x234500000000);
            for _ in 0..7 {new.assertions.push(Assertion{message:"modeled prior",function:"other",kind:FaultKind::Assertion});}
            let mut outcomes=vec![];let mut key_ns=0;let mut restore_ns=0;let mut fresh_ns=0;let mut words=0;
            for (&id,template) in &templates {
                let start=Instant::now();let key=identity_mode(&current,&new,id,&emitter,MAX_KEY_BYTES,true);
                key_ns+=start.elapsed().as_nanos();
                if key!=Some(template.key) {outcomes.push((id,"key_miss"));continue;}
                let start=Instant::now();let restored=template.restore(&current,&new,id,&emitter,MAX_CODE_BYTES/4);
                restore_ns+=start.elapsed().as_nanos();
                let Some(restored)=restored else {outcomes.push((id,"restore_miss"));continue;};
                let start=Instant::now();let fresh=new.emit_function(&q.functions[id],MAX_CODE_BYTES/4).unwrap().unwrap();
                fresh_ns+=start.elapsed().as_nanos();
                tests::same(&restored,&fresh);words+=restored.words.len();outcomes.push((id,"exact"));
            }
            assert!(old.code.is_none() && new.code.is_none());assert_eq!(old.bytes+new.bytes,0);
            comparisons.push(serde_json::json!({"ordinal":ordinal,"state":artifact.state,"artifact_sha256":artifact.sha256,
                "scalar_entries":new_scalars,"outcomes":outcomes,"exact_words":words,
                "diagnostic_ns":{"key_all":key_ns,"restore_key_matches":restore_ns,"fresh_exact":fresh_ns}}));
        }
        reports.push(serde_json::json!({"worker":worker.worker,"observed_functions":worker.functions.len(),
            "scalar_entries":old_scalars,"templates":templates.len(),"retained_charge":retained,"declines":declines,"comparisons":comparisons}));
    }
    let report=serde_json::json!({"schema_version":1,"input_sha256":digest(&input_bytes),"workers":reports,
        "original_project_guest_commands":0,"executable_code_publications":0,"production_cache_admission":false,
        "scalar_admission":"modeled current proof in ascending callee order; synthetic addresses; no arena accounting",
        "scope":"Saved original active functions versus seven checked artifacts. Exact staging only; diagnostic test-mode intervals are not end-to-end measurements or predicted savings."});
    let bytes=serde_json::to_vec(&report).unwrap();assert!(bytes.len()<=16*1024*1024);
    use std::io::Write;
    let mut file=std::fs::OpenOptions::new().write(true).create_new(true).open(output_path).unwrap();file.write_all(&bytes).unwrap();
}

#[test]
#[ignore="requires closed history controls and explicit saved artifacts; no guest execution"]
fn cross_program_template_replay_populated_parser_history() {
    let input_path=std::env::var("RUST_INTERP_TEMPLATE_REPLAY_INPUT").unwrap();
    let output_path=std::env::var("RUST_INTERP_TEMPLATE_REPLAY_OUTPUT").unwrap();
    let input_bytes=read(&input_path,16*1024*1024);let input:Input=serde_json::from_slice(&input_bytes).unwrap();
    assert_eq!(input.artifacts.iter().map(|a|a.state).collect::<Vec<_>>(),[0,-1,1,2,3,4,5,0]);
    assert_eq!(input.workers.iter().map(|w|w.worker).collect::<Vec<_>>(),[0,1]);
    let emitter:[u8;32]=[29;32];let mut reports=vec![];
    for worker in &input.workers {
        assert!(worker.functions.len()<=16_384);
        assert!(worker.functions.windows(2).all(|pair|pair[0].function<pair[1].function));
        let mut history=History::new(MAX_RETAINED).unwrap();let mut comparisons=vec![];
        for (ordinal,artifact) in input.artifacts.iter().enumerate() {
            let p=program(artifact);let checked=Checked::new(&p).unwrap();
            if ordinal==0 {
                for row in &worker.functions {
                    let f=&p.functions[row.function];assert_eq!(f.name,row.name);assert_eq!(f.code.len(),row.operations);
                    assert_eq!(digest(&bincode::serialize(f).unwrap()),row.sha256);
                }
            }
            let (mut jit,scalars)=owner(&p,worker,0x123400000000+ordinal*0x10000000000);
            for _ in 0..ordinal {jit.assertions.push(Assertion{message:"modeled prior",function:"other",kind:FaultKind::Assertion});}
            let (mut key_ns,mut restore_ns,mut fresh_ns,mut fresh_exact_ns,mut insert_ns)=(0,0,0,0,0);
            let (mut words,mut inserted,mut capture_declines,mut emission_declines)=(0,0,0,0);
            let before_evictions=history.evictions;let mut outcomes=vec![];
            for row in &worker.functions {
                let id=row.function;
                let Some(_)=p.functions.get(id) else {outcomes.push((id,"unavailable"));continue;};
                let start=Instant::now();let request=Request::new(&checked,&jit,id,emitter,true)
                    .expect("all keys in the closed history fit the unchanged identity bounds");
                key_ns+=start.elapsed().as_nanos();
                let start=Instant::now();let mut outcome="key_miss";
                let restored=history.get(&request.key).and_then(|template|{
                    outcome="restore_miss";template.restore_request(&request,MAX_CODE_BYTES/4)
                });
                restore_ns+=start.elapsed().as_nanos();
                let start=Instant::now();
                let fresh=match request.emit(MAX_CODE_BYTES/4) {
                    Ok(staged)=>staged,Err(EmitError::Limit(_))=>None,
                    Err(error)=>panic!("invalid fresh history staging for {id}: {error:?}"),
                };
                let nanos=start.elapsed().as_nanos();fresh_ns+=nanos;
                if let Some(restored)=restored {
                    let fresh=fresh.as_ref().expect("restoration succeeded but fresh emission declined");
                    tests::same(&restored,&fresh.compiled);words+=restored.words.len();fresh_exact_ns+=nanos;outcome="exact";
                } else if let Some(fresh)=fresh {
                    let start=Instant::now();
                    let stored=Template::capture_emission(&fresh,MAX_RETAINED).and_then(|template|history.insert(template));
                    if stored.is_some() {inserted+=1;} else {capture_declines+=1;}
                    insert_ns+=start.elapsed().as_nanos();
                } else {emission_declines+=1;}
                outcomes.push((id,outcome));
            }
            assert!(jit.code.is_none());assert_eq!(jit.bytes,0);
            assert!(history.charge<=MAX_RETAINED && history.entries.len()<=16_384);
            assert_eq!(history.entries.len(),history.order.len());
            comparisons.push(serde_json::json!({"ordinal":ordinal,"state":artifact.state,"artifact_sha256":artifact.sha256,
                "scalar_entries":scalars,"outcomes":outcomes,"exact_words":words,"inserted":inserted,
                "capture_declines":capture_declines,"emission_declines":emission_declines,
                "evictions":history.evictions-before_evictions,"history_entries":history.entries.len(),"history_charge":history.charge,
                "diagnostic_ns":{"key_all":key_ns,"lookup_restore":restore_ns,"fresh_all":fresh_ns,
                    "fresh_exact":fresh_exact_ns,"capture_insert":insert_ns}}));
        }
        reports.push(serde_json::json!({"worker":worker.worker,"observed_functions":worker.functions.len(),"comparisons":comparisons}));
    }
    let report=serde_json::json!({"schema_version":1,"populated_history":true,"bound_requests":true,"input_sha256":digest(&input_bytes),"workers":reports,
        "original_project_guest_commands":0,"executable_code_publications":0,"production_cache_admission":false,
        "scalar_admission":"modeled current proof in ascending callee order; synthetic addresses; no arena accounting",
        "scope":"Bounded populated staging history over eight actual artifacts and fixed original numeric function sets. Every hit equals fresh staging. Later reachability/order is not measured. Test-mode intervals exclude storage and publication; no predicted command saving."});
    let bytes=serde_json::to_vec(&report).unwrap();assert!(bytes.len()<=16*1024*1024);
    use std::io::Write;
    let mut file=std::fs::OpenOptions::new().write(true).create_new(true).open(output_path).unwrap();file.write_all(&bytes).unwrap();
}
