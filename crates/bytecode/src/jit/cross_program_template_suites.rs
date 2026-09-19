//! Explicit real-suite correctness replay with native reuse verified before publication.
use super::*;
use bincode::Options;
use serde::Deserialize;
use serde_json::{Value,json};
use std::sync::{Barrier,Mutex,atomic::{AtomicBool,AtomicUsize,Ordering}};

#[derive(Deserialize)]
struct Case {
    state:i32,artifact_path:String,artifact_sha256:String,catalog_path:String,catalog_sha256:String,
    expected:Vec<(String,String)>,
}
#[derive(Deserialize)]
struct Input {cases:Vec<Case>,disk_path:String}
fn bytes(path:&str,limit:u64,digest:Option<&str>)->Vec<u8> {
    use std::io::Read;
    let file=std::fs::File::open(path).unwrap();assert!(file.metadata().unwrap().is_file() && file.metadata().unwrap().len()<=limit);
    let mut bytes=vec![];file.take(limit+1).read_to_end(&mut bytes).unwrap();assert!(bytes.len() as u64<=limit);
    if let Some(digest)=digest {assert_eq!(format!("{:x}",Sha256::digest(&bytes)),digest);}
    bytes
}
fn space(path:&str) {
    let out=std::process::Command::new("/bin/df").args(["-k",path]).output().unwrap();assert!(out.status.success());
    let text=String::from_utf8(out.stdout).unwrap();let line=text.lines().last().unwrap();
    let free=line.split_whitespace().nth(3).unwrap().parse::<u64>().unwrap()*1024;
    assert!(free>=8*1024*1024*1024,"suite disk admission below8GiB");
}
fn limits()->crate::Limits {
    crate::Limits{instructions:100_000_000_000,allocations:150_000,memory:64*1024*1024,frames:4096,
        jit_code_bytes:MAX_CODE_BYTES,jit_resumable_calls:true,jit_persistent_registers:true,jit_scalar_calls:true,..Default::default()}
}
fn run_case(case:&Case,next:&AtomicUsize,history:std::rc::Rc<std::cell::RefCell<History>>,cached:bool)->Value {
    let data=bytes(&case.artifact_path,64*1024*1024,Some(&case.artifact_sha256));
    let program:Program=bincode::DefaultOptions::new().with_fixint_encoding().with_limit(64*1024*1024)
        .reject_trailing_bytes().deserialize(&data).unwrap();
    let catalog:crate::EntryCatalog=serde_json::from_slice(&bytes(&case.catalog_path,4*1024*1024,Some(&case.catalog_sha256))).unwrap();
    let entries=catalog.validated_entries(&program,&data).unwrap();
    let expected=case.expected.iter().map(|(n,s)|(n.as_str(),s.as_str())).collect::<BTreeMap<_,_>>();
    assert_eq!(expected.len(),case.expected.len());assert_eq!(entries.len(),114);
    assert_eq!(entries.iter().map(|(n,_)|*n).collect::<BTreeSet<_>>(),expected.keys().copied().collect());
    let context=if cached {Some(Context::new_verified(&program,history.clone(),true).unwrap())}
        else {Checked::new(&program).unwrap();None};
    let mut jit=Jit::new_resumable(&program,false,MAX_CODE_BYTES,true).unwrap();jit.enable_scalar_calls();
    jit.template_model_context=context.clone();let mut jit=Some(jit);
    let metadata=crate::ExecutionMetadata::new(&program,jit.as_ref(),true,limits().memory).unwrap();
    let mut outcomes=vec![];
    loop {
        let index=next.fetch_add(1,Ordering::Relaxed);let Some(&(name,id))=entries.get(index) else {break;};
        let result=crate::execute_prepared_impl::<false,true,false,false,true>(&program,id,&[],limits(),None,&mut jit,&metadata);
        let outcome=match result {
            Ok(run)=>json!({"index":index,"name":name,"function":id,"status":"passed","value":run.value,
                "instructions":run.instructions,"jit_instructions":run.jit_instructions,"jit_entries":run.jit_entries,
                "peak_guest_memory":run.peak_memory}),
            Err(error)=>json!({"index":index,"name":name,"function":id,"status":"failed","error":error}),
        };
        assert_eq!(outcome["status"].as_str().unwrap(),expected[name],"original outcome changed for {name}");
        outcomes.push(outcome);
    }
    let owner=jit.as_ref().unwrap();let counts=context.as_ref().map(|c|{
        let counts=c.counts.borrow();assert_eq!(counts.hits,counts.verified_hits);serde_json::to_value(&*counts).unwrap()
    });
    let retained=history.borrow();assert!(retained.charge<=MAX_RETAINED && retained.entries.len()<=16_384);
    json!({"status":"passed","outcomes":outcomes,"cache":counts,"history_charge":retained.charge,
        "history_entries":retained.entries.len(),"history_evictions":retained.evictions,
        "code_bytes":owner.bytes,"compiled_functions":owner.compiled_functions,"declined_functions":owner.declined_functions})
}
fn journal(writer:&Mutex<(std::fs::File,usize)>,record:&Value)->Result<(),String> {
    use std::io::Write;
    let bytes=serde_json::to_vec(record).map_err(|e|e.to_string())?;
    if bytes.len()>4*1024*1024 {return Err("case journal record exceeds4MiB".into());}
    let mut guard=writer.lock().map_err(|_|"journal lock poisoned")?;
    let charge=guard.1.checked_add(bytes.len()+1).filter(|&n|n<=16*1024*1024).ok_or("journal exceeds16MiB")?;
    guard.0.write_all(&bytes).and_then(|_|guard.0.write_all(b"\n")).and_then(|_|guard.0.flush())
        .and_then(|_|guard.0.sync_data()).map_err(|e|e.to_string())?;
    guard.1=charge;Ok(())
}

#[test]
#[ignore="requires closed workspace/focused controls and exact saved parser suite inputs"]
#[cfg(all(target_arch="aarch64",target_os="macos"))]
fn cross_program_template_execute_saved_parser_suites() {
    let input_path=std::env::var("RUST_INTERP_TEMPLATE_SUITES_INPUT").unwrap();
    let output_path=std::path::PathBuf::from(std::env::var("RUST_INTERP_TEMPLATE_SUITES_OUTPUT").unwrap());
    let raw=bytes(&input_path,4*1024*1024,None);let input:Input=serde_json::from_slice(&raw).unwrap();
    assert_eq!(input.cases.iter().map(|c|c.state).collect::<Vec<_>>(),[0,-1,1,2,3,4,5,0]);
    for case in &input.cases {
        assert_eq!(case.expected.len(),114);
        assert!(case.expected.iter().all(|(_,s)|s=="passed" || s=="failed"));
        assert_eq!(case.expected.iter().any(|(_,s)|s=="failed"),case.state==-1);
    }
    // Reserve all outputs before any guest runs. Sync each worker/case record
    // before advancing so completed cases survive a later process failure.
    let mut output=std::fs::OpenOptions::new().write(true).create_new(true).open(&output_path).unwrap();
    let journal_file=std::fs::OpenOptions::new().write(true).create_new(true).open(output_path.with_extension("jsonl")).unwrap();
    let writer=Mutex::new((journal_file,0));let mut records=vec![];let mut failed=false;
    for cached in [false,true] {
        let next=(0..input.cases.len()).map(|_|AtomicUsize::new(0)).collect::<Vec<_>>();
        let barrier=Barrier::new(2);let abort=AtomicBool::new(false);
        let workers=std::thread::scope(|scope|{
            let mut handles=vec![];
            for worker in 0..2 {
                let next=&next;let barrier=&barrier;let abort=&abort;let writer=&writer;let input=&input;
                handles.push(scope.spawn(move ||{
                    // History and every JIT are born, used and dropped here.
                    // No native arena/owner crosses a thread boundary.
                    let history=std::rc::Rc::new(std::cell::RefCell::new(History::new(MAX_RETAINED).unwrap()));
                    let mut rows=vec![];
                    for (ordinal,case) in input.cases.iter().enumerate() {
                        let attempted=std::panic::catch_unwind(std::panic::AssertUnwindSafe(||{
                            space(&input.disk_path);run_case(case,&next[ordinal],history.clone(),cached)
                        }));
                        let mut row=match attempted {
                            Ok(row)=>row,
                            Err(error)=>{
                                abort.store(true,Ordering::SeqCst);
                                let message=error.downcast_ref::<String>().cloned().or_else(||error.downcast_ref::<&str>().map(|s|s.to_string()))
                                    .unwrap_or_else(||"non-string worker panic".into());
                                json!({"status":"failed","diagnostic_error":message.chars().take(4096).collect::<String>()})
                            },
                        };
                        row["mode"]=if cached {"cached"} else {"fresh"}.into();row["worker"]=worker.into();
                        row["ordinal"]=ordinal.into();row["state"]=case.state.into();row["artifact_sha256"]=case.artifact_sha256.clone().into();
                        if let Err(error)=journal(writer,&row) {row["journal_error"]=error.into();abort.store(true,Ordering::SeqCst);}
                        rows.push(row);
                        // Even a caught setup/guest/verifier failure reaches the
                        // rendezvous, preventing a peer stranded on the barrier.
                        barrier.wait();if abort.load(Ordering::SeqCst) {break;}
                    }
                    rows
                }));
            }
            handles.into_iter().map(|h|h.join().unwrap()).collect::<Vec<_>>()
        });
        for rows in workers {records.extend(rows);}
        if abort.load(Ordering::SeqCst) {failed=true;break;}
    }
    let recorded_tests=records.iter().filter_map(|r|r["outcomes"].as_array()).map(Vec::len).sum::<usize>();
    if !failed {assert_eq!(recorded_tests,1824);}
    let report=json!({"schema_version":1,"input_sha256":format!("{:x}",Sha256::digest(&raw)),"records":records,
        "status":if failed {"failed"} else {"passed"},"workers":2,"planned_suite_executions":16,
        "planned_test_invocations":1824,"recorded_test_invocations":recorded_tests,
        "guest_execution":true,"executable_code_publication":true,"verify_every_cache_hit":true,
        "production_cache_admission":false,"performance_measurement":false,
        "scope":"Saved-artifact suite correctness and actual reachability; fresh emission verifies every hit. No source build, persistent storage, or end-to-end speedup measurement."});
    use std::io::Write;
    let report_bytes=serde_json::to_vec(&report).unwrap();assert!(report_bytes.len()<=16*1024*1024);output.write_all(&report_bytes).unwrap();
    assert!(!failed,"real-suite replay failed; completed case records retained");
}
