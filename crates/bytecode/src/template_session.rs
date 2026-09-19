//! Explicit inherited-pipe session. Native templates never enter the protocol.
use bincode::Options;
use rust_interp_bytecode::{EntryCatalog,Limits,PreparedJit,Program,TemplateHistory};
use serde::{Deserialize,Serialize};
use serde_json::{Value,json};
use sha2::{Digest,Sha256};
use std::{io::{Read,Write},path::Path,sync::{Arc,mpsc,atomic::{AtomicUsize,Ordering}},time::Instant};

const MAX_FRAME:usize=4*1024*1024;
const WORKERS:usize=2;
type Environment=Vec<(Vec<u8>,Vec<u8>)>;
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Binding {path:String,sha256:String}
#[derive(Clone,Deserialize)]
#[serde(deny_unknown_fields)]
struct Budget {instructions:u64,allocations:usize,memory_bytes:usize,frames:usize,code_bytes:usize,
    persistent_registers:bool,scalar_calls:bool}
impl Budget {
    fn limits(&self)->Result<Limits,String> {
        if self.instructions>100_000_000_000 || self.allocations>rust_interp_bytecode::MAX_ALLOCATION_LIMIT
            || self.memory_bytes>64*1024*1024 || self.frames>4096 || self.code_bytes>16*1024*1024 {
            return Err("request exceeds supported runtime bounds".into());
        }
        Ok(Limits{instructions:self.instructions,allocations:self.allocations,memory:self.memory_bytes,frames:self.frames,
            jit_code_bytes:self.code_bytes,jit_resumable_calls:true,jit_persistent_registers:self.persistent_registers,
            jit_scalar_calls:self.scalar_calls,..Default::default()})
    }
}
#[derive(Deserialize)]
#[serde(tag="command",rename_all="snake_case",deny_unknown_fields)]
enum Body {
    Run {artifact:Binding,catalog:Binding,report:String,cwd:String,budget:Budget,environment:Environment},
    Shutdown,
}
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Request {schema:u32,id:u64,body:Body}

fn read_frame(reader:&mut impl Read)->Result<Option<Vec<u8>>,String> {
    let mut length=[0;4];
    loop {match reader.read(&mut length[..1]) {
        Ok(0)=>return Ok(None),Ok(_)=>break,
        Err(error) if error.kind()==std::io::ErrorKind::Interrupted=>continue,
        Err(error)=>return Err(error.to_string()),
    }}
    reader.read_exact(&mut length[1..]).map_err(|e|e.to_string())?;
    let length=u32::from_le_bytes(length) as usize;
    if length==0 || length>MAX_FRAME {return Err("invalid session frame length".into());}
    let mut bytes=vec![0;length];reader.read_exact(&mut bytes).map_err(|e|e.to_string())?;Ok(Some(bytes))
}
fn write_frame(writer:&mut impl Write,value:&Value)->Result<(),String> {
    let bytes=serde_json::to_vec(value).map_err(|e|e.to_string())?;
    if bytes.len()>MAX_FRAME {return Err("session response exceeds bound".into());}
    writer.write_all(&(bytes.len() as u32).to_le_bytes()).and_then(|_|writer.write_all(&bytes))
        .and_then(|_|writer.flush()).map_err(|e|e.to_string())
}
fn absolute(path:&str)->Result<&Path,String> {
    let path=Path::new(path);
    if !path.is_absolute() || path.as_os_str().len()>4096 {return Err("session paths must be bounded and absolute".into());}
    Ok(path)
}
fn read_bound(binding:&Binding,limit:usize)->Result<Vec<u8>,String> {
    let file=std::fs::File::open(absolute(&binding.path)?).map_err(|e|e.to_string())?;
    let metadata=file.metadata().map_err(|e|e.to_string())?;
    if !metadata.is_file() || metadata.len()>limit as u64 {return Err("session input file exceeds bound or is not regular".into());}
    let mut bytes=vec![];file.take(limit as u64+1).read_to_end(&mut bytes).map_err(|e|e.to_string())?;
    if bytes.len()>limit || format!("{:x}",Sha256::digest(&bytes))!=binding.sha256 {
        return Err("session input digest or size differs".into());
    }
    Ok(bytes)
}
fn environment_bound(pairs:&Environment)->Result<(),String> {
    if pairs.len()>4096 {return Err("session environment exceeds binding count".into());}
    let mut total=0usize;
    for (name,value) in pairs {
        total=total.checked_add(name.len()).and_then(|n|n.checked_add(value.len()+128)).ok_or("environment size overflow")?;
        if total>1024*1024 || name.contains(&0) || value.contains(&0) {return Err("invalid or oversized session environment".into());}
    }
    Ok(())
}

struct Job {program:Arc<Program>,entries:Arc<Vec<(String,usize)>>,next:Arc<AtomicUsize>,limits:Limits,
    environment:Arc<Environment>,reply:mpsc::SyncSender<Value>}
struct Pool {senders:Vec<mpsc::SyncSender<Job>>,handles:Vec<std::thread::JoinHandle<()>>,poisoned:bool}
impl Pool {
    fn new(bytes:usize,verify:bool)->Result<Self,String> {
        if bytes!=0 && !(512..=64*1024*1024).contains(&bytes) {return Err("invalid history capacity".into());}
        let mut pool=Self{senders:vec![],handles:vec![],poisoned:false};
        for worker in 0..WORKERS {
            let (tx,rx)=mpsc::sync_channel::<Job>(1);
            let handle=std::thread::Builder::new().name(format!("template-session-{worker}"))
                .spawn(move ||{
                    // Rc history and every native owner originate on this thread.
                    let history=(bytes!=0).then(||TemplateHistory::new(bytes,verify).unwrap());
                    while let Ok(job)=rx.recv() {
                        let result=std::panic::catch_unwind(std::panic::AssertUnwindSafe(||worker_run(&job,history.as_ref())));
                        let (mut row,poisoned)=match result {
                            Ok(Ok(row))=>(row,false),
                            Ok(Err(error))=>(json!({"status":"setup-failed","error":error}),false),
                            Err(_)=>(json!({"status":"worker-panicked"}),true),
                        };
                        row["worker"]=worker.into();row["poisoned"]=poisoned.into();
                        if job.reply.send(row).is_err() || poisoned {break;}
                    }
                }).map_err(|e|format!("cannot start session worker: {e}"))?;
            pool.senders.push(tx);pool.handles.push(handle);
        }
        Ok(pool)
    }
    fn run(&mut self,program:Program,entries:Vec<(String,usize)>,limits:Limits,environment:Environment)->Result<Vec<Value>,String> {
        let program=Arc::new(program);let entries=Arc::new(entries);let next=Arc::new(AtomicUsize::new(0));
        let environment=Arc::new(environment);let (tx,rx)=mpsc::sync_channel(WORKERS);
        for sender in &self.senders {
            if sender.send(Job{program:program.clone(),entries:entries.clone(),next:next.clone(),limits:limits.clone(),
                environment:environment.clone(),reply:tx.clone()}).is_err() {
                self.poisoned=true;return Err("session worker disconnected; execution may have started".into());
            }
        }
        drop(tx);let mut rows=vec![];
        for _ in 0..WORKERS {match rx.recv() {
            Ok(row)=>rows.push(row),Err(_)=>{self.poisoned=true;return Err("session response lost; execution may have completed".into());},
        }}
        rows.sort_by_key(|r|r["worker"].as_u64());Ok(rows)
    }
}
impl Drop for Pool {
    fn drop(&mut self) {
        self.senders.clear();
        for handle in self.handles.drain(..) {let _=handle.join();}
    }
}
fn worker_run(job:&Job,history:Option<&TemplateHistory>)->Result<Value,String> {
    let mut owner=PreparedJit::with_session_inputs(&job.program,&job.limits,history,&job.environment)?;
    let preparation=owner.preparation_nanos();let mut outcomes=vec![];
    loop {
        let index=job.next.fetch_add(1,Ordering::Relaxed);
        let Some((name,id))=job.entries.get(index) else {break;};
        let started=Instant::now();let run=owner.execute_entry(*id,&[],job.limits.clone());
        let mut outcome=match run {
            Ok(run)=>json!({"index":index,"name":name,"function":id,"status":"passed","value":run.value,
                "instructions":run.instructions,"peak_guest_memory":run.peak_memory,"jit_compile_ns":run.jit_compile_nanos,
                "jit_bytes":run.jit_bytes,"jit_compiled_functions":run.jit_compiled_functions,
                "jit_declined_functions":run.jit_declined_functions,"jit_instructions":run.jit_instructions,"jit_entries":run.jit_entries}),
            Err(error)=>{
                if error.len()>4096 {return Err("guest diagnostic exceeds session report bound".into());}
                json!({"index":index,"name":name,"function":id,"status":"failed","error":error})
            },
        };
        outcome["seconds"]=started.elapsed().as_secs_f64().into();outcomes.push(outcome);
    }
    Ok(json!({"status":"completed","tests":outcomes,"preparation_ns":preparation,
        "templates":owner.template_statistics(),"storage":history.map(TemplateHistory::storage)}))
}

// Darwin SDK sys/resource.h: two timevals followed by fourteen long fields.
// arm/_types.h defines time_t as long; sys/_types.h defines suseconds_t as i32.
#[derive(Clone,Copy,Serialize)]
struct Cpu {user_us:u64,system_us:u64}
#[cfg(all(target_arch="aarch64",target_os="macos"))]
fn cpu()->Result<Cpu,String> {
    #[repr(C)] struct Timeval {seconds:std::ffi::c_long,micros:i32}
    #[repr(C)] struct Rusage {user:Timeval,system:Timeval,opaque:[std::ffi::c_long;14]}
    const _:()={assert!(std::mem::size_of::<Timeval>()==16);assert!(std::mem::size_of::<Rusage>()==144);};
    unsafe extern "C" {fn getrusage(who:i32,out:*mut Rusage)->i32;}
    let mut out=std::mem::MaybeUninit::<Rusage>::uninit();
    // SAFETY: correctly aligned writable Darwin rusage; read only on success.
    if unsafe{getrusage(0,out.as_mut_ptr())}!=0 {return Err(std::io::Error::last_os_error().to_string());}
    let out=unsafe{out.assume_init()};
    let micros=|t:Timeval|->Result<u64,String>{
        if t.seconds<0 || !(0..1_000_000).contains(&t.micros) {return Err("invalid process CPU snapshot".into());}
        (t.seconds as u64).checked_mul(1_000_000).and_then(|n|n.checked_add(t.micros as u64)).ok_or("process CPU overflow".into())
    };
    Ok(Cpu{user_us:micros(out.user)?,system_us:micros(out.system)?})
}
#[cfg(not(all(target_arch="aarch64",target_os="macos")))]
fn cpu()->Result<Cpu,String> {Err("template sessions require AArch64 macOS".into())}

fn run_request(pool:&mut Pool,id:u64,body:Body)->Result<Value,String> {
    let Body::Run{artifact,catalog,report,cwd,budget,environment}=body else {return Err("expected run request".into());};
    if absolute(&cwd)?!=std::env::current_dir().map_err(|e|e.to_string())? {return Err("session working directory differs".into());}
    let limits=budget.limits()?;environment_bound(&environment)?;
    let bytes=read_bound(&artifact,64*1024*1024)?;
    let program:Program=bincode::DefaultOptions::new().with_fixint_encoding().with_limit(64*1024*1024)
        .reject_trailing_bytes().deserialize(&bytes).map_err(|e|e.to_string())?;
    let catalog_bytes=read_bound(&catalog,4*1024*1024)?;
    let catalog_value:EntryCatalog=serde_json::from_slice(&catalog_bytes).map_err(|e|e.to_string())?;
    let entries=catalog_value.validated_entries(&program,&bytes)?.into_iter().map(|(n,id)|(n.to_owned(),id)).collect::<Vec<_>>();
    let total=entries.len();rust_interp_bytecode::validate(&program)?;
    // Reject unsafe/unsupported session host I/O through the unchanged runtime
    // admission (no descriptor/getcwd options in this initial protocol).
    let mut file=std::fs::OpenOptions::new().write(true).create_new(true).open(absolute(&report)?).map_err(|e|e.to_string())?;
    let started=Instant::now();let rows=pool.run(program,entries,limits.clone(),environment)?;
    let poisoned=rows.iter().any(|r|r["poisoned"]==true);
    let complete=rows.iter().all(|r|r["status"]=="completed");
    let mut tests=rows.iter().filter_map(|r|r["tests"].as_array()).flatten().cloned().collect::<Vec<_>>();
    tests.sort_by_key(|r|r["index"].as_u64());
    let coverage=tests.len()==total && tests.iter().enumerate().all(|(i,r)|r["index"].as_u64()==Some(i as u64));
    let failures=tests.iter().filter(|r|r["status"]=="failed").count();
    let status=if !complete || !coverage {"incomplete"} else if failures>0 {"failed"} else {"passed"};
    let result=json!({"schema_version":1,"request_id":id,"status":status,"mode":"prepared","workers":WORKERS,
        "selected":total,"completed":tests.len(),"passed":tests.len().saturating_sub(failures),"failed":failures,
        "tests":tests,"worker_records":rows,
        "artifact_sha256":artifact.sha256,"catalog_sha256":catalog.sha256,"poisoned":poisoned,
        "runtime_limits":{"instructions":limits.instructions,"allocations":limits.allocations,"memory_bytes":limits.memory,"frames":limits.frames},
        "jit_code_limit_bytes":limits.jit_code_bytes,"seconds_before_report_write":started.elapsed().as_secs_f64(),
        "scope":"selected test bodies; fresh native owners and guest state, per-request environment; no source build or libtest/thread/unwind semantics"});
    let bytes=serde_json::to_vec(&result).map_err(|e|e.to_string())?;
    if bytes.len()>MAX_FRAME {return Err("session report exceeds bound".into());}
    file.write_all(&bytes).and_then(|_|file.flush()).and_then(|_|file.sync_data()).map_err(|e|e.to_string())?;
    Ok(json!({"kind":"result","id":id,"status":status,"poisoned":poisoned,"report":report,
        "report_sha256":format!("{:x}",Sha256::digest(&bytes))}))
}
fn serve()->Result<(),String> {
    let args=std::env::args().skip(1).collect::<Vec<_>>();
    if !(args.len()==3 || args.len()==4) || args[0]!="--serve-stdio" || args[1]!="--history-bytes"
        || (args.len()==4 && args[3]!="--verify-hits") {return Err("usage: rust-interp-template-session --serve-stdio --history-bytes N [--verify-hits]".into());}
    let bytes=args[2].parse::<usize>().map_err(|e|e.to_string())?;let verify=args.len()==4;
    let startup=cpu()?;let mut pool=Pool::new(bytes,verify)?;
    let executable=std::env::current_exe().map_err(|e|e.to_string())?;
    let file=std::fs::File::open(executable).map_err(|e|e.to_string())?;
    if file.metadata().map_err(|e|e.to_string())?.len()>128*1024*1024 {return Err("session executable exceeds identity bound".into());}
    let mut executable=vec![];file.take(128*1024*1024+1).read_to_end(&mut executable).map_err(|e|e.to_string())?;
    if executable.len()>128*1024*1024 {return Err("session executable grew beyond identity bound".into());}
    let mut input=std::io::stdin().lock();let mut output=std::io::stdout().lock();
    write_frame(&mut output,&json!({"kind":"ready","schema":1,"pid":std::process::id(),"workers":WORKERS,
        "history_bytes_per_worker":bytes,"verify_hits":verify,"executable_sha256":format!("{:x}",Sha256::digest(&executable)),
        "cpu_at_entry":startup,"cpu_at_ready":cpu()?}))?;
    let mut expected=1u64;
    loop {
        let before=cpu()?;let Some(frame)=read_frame(&mut input)? else {break;};
        let request:Request=serde_json::from_slice(&frame).map_err(|e|e.to_string())?;
        if request.schema!=1 || request.id!=expected || expected>4096 {return Err("session request schema, sequence or count differs".into());}
        expected+=1;
        if matches!(request.body,Body::Shutdown) {break;}
        let started=Instant::now();let mut response=match run_request(&mut pool,request.id,request.body) {
            Ok(result)=>result,
            Err(error)=>json!({"kind":"error","id":request.id,"error":error.chars().take(4096).collect::<String>(),
                "execution_possible":true,"poisoned":pool.poisoned}),
        };
        response["cpu_before"]=serde_json::to_value(before).unwrap();response["cpu_after"]=serde_json::to_value(cpu()?).unwrap();
        response["request_seconds"]=started.elapsed().as_secs_f64().into();
        let poisoned=response["poisoned"]==true;write_frame(&mut output,&response)?;
        if poisoned {return Err("session worker failed; session closed".into());}
    }
    drop(pool);
    write_frame(&mut output,&json!({"kind":"closed","requests_consumed":expected-1,"cpu_at_close":cpu()?}))
}
fn main() {
    if let Err(error)=serve() {eprintln!("rust-interp-template-session: {}",error.chars().take(4096).collect::<String>());std::process::exit(1);}
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn framed_requests_reject_truncation_zero_and_oversized_lengths() {
        assert!(read_frame(&mut &[][..]).unwrap().is_none());
        for bytes in [vec![1],0u32.to_le_bytes().to_vec(),((MAX_FRAME+1) as u32).to_le_bytes().to_vec(),vec![2,0,0,0,b'{']] {
            assert!(read_frame(&mut &bytes[..]).is_err());
        }
        let mut bytes=vec![];write_frame(&mut bytes,&json!({"sample":1})).unwrap();
        assert_eq!(serde_json::from_slice::<Value>(&read_frame(&mut &bytes[..]).unwrap().unwrap()).unwrap(),json!({"sample":1}));
    }
    #[test]
    fn input_bounds_and_unknown_protocol_fields_are_rejected() {
        assert!(environment_bound(&vec![(vec![0],vec![])]).is_err());
        assert!(environment_bound(&vec![(b"x".to_vec(),vec![1;1024*1024])]).is_err());
        assert!(serde_json::from_value::<Request>(json!({"schema":1,"id":1,"body":{"command":"shutdown","unknown":1}})).is_err());
        assert!(absolute("relative").is_err());
    }
    #[test]
    #[cfg(all(target_arch="aarch64",target_os="macos"))]
    fn process_cpu_snapshots_are_monotonic() {
        let a=cpu().unwrap();let b=cpu().unwrap();assert!(b.user_us>=a.user_us && b.system_us>=a.system_us);
    }
}
