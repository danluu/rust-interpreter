#![cfg(all(feature="jit-template-session",target_arch="aarch64",target_os="macos"))]
use rust_interp_bytecode::{EntryCatalog,Function,Op,Program,SelectedEntry,Slot,VERSION};
use serde_json::{Value,json};
use sha2::{Digest,Sha256};
use std::{io::{Read,Write},path::{Path,PathBuf},process::{Child,ChildStdin,ChildStdout,Command,Stdio}};

fn digest(bytes:&[u8])->String {format!("{:x}",Sha256::digest(bytes))}
fn directory(label:&str)->PathBuf {
    let base=std::env::var_os("RUST_INTERP_SESSION_FIXTURES").map(PathBuf::from).unwrap_or_else(std::env::temp_dir);
    let path=base.join(format!("template-session-{}-{label}",std::process::id()));std::fs::create_dir(&path).unwrap();path
}
struct Session {child:Child,input:Option<ChildStdin>,output:ChildStdout,ready:Value,folder:PathBuf,next:u64}
impl Session {
    fn start(label:&str,history:usize)->Self {
        let args=["--serve-stdio".to_owned(),"--history-bytes".into(),history.to_string(),"--verify-hits".into()];
        let mut session=Self::launch(label,&args);session.initialize();session
    }
    fn launch(label:&str,args:&[String])->Self {
        let folder=directory(label);let executable=env!("CARGO_BIN_EXE_rust-interp-template-session");
        let stderr=std::fs::OpenOptions::new().write(true).create_new(true).open(folder.join("stderr.log")).unwrap();
        let mut child=Command::new(executable).args(args).stdin(Stdio::piped()).stdout(Stdio::piped()).stderr(stderr).spawn().unwrap();
        let receipt=json!({"pid":child.id(),"parent_pid":std::process::id(),"executable":executable,"args":args,
            "cwd":std::env::current_dir().unwrap(),"started_epoch":std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64()});
        let input=child.stdin.take();let output=child.stdout.take().unwrap();
        let session=Self{child,input,output,ready:Value::Null,folder,next:1};
        std::fs::write(session.folder.join("child.json"),serde_json::to_vec(&receipt).unwrap()).unwrap();
        session
    }
    fn initialize(&mut self) {
        self.ready=self.read();let session=self;let executable=env!("CARGO_BIN_EXE_rust-interp-template-session");
        assert_eq!(session.ready["kind"],"ready");assert_eq!(session.ready["pid"],session.child.id());
        assert_eq!(session.ready["executable_sha256"],digest(&std::fs::read(executable).unwrap()));
        std::fs::write(session.folder.join("ready.json"),serde_json::to_vec(&session.ready).unwrap()).unwrap();
    }
    fn read(&mut self)->Value {
        let mut length=[0;4];self.output.read_exact(&mut length).unwrap();let n=u32::from_le_bytes(length) as usize;
        assert!(n>0 && n<=4*1024*1024);let mut bytes=vec![0;n];self.output.read_exact(&mut bytes).unwrap();serde_json::from_slice(&bytes).unwrap()
    }
    fn send(&mut self,body:Value)->Value {
        let id=self.next;self.next+=1;let request=json!({"schema":1,"id":id,"body":body});
        let bytes=serde_json::to_vec(&request).unwrap();let input=self.input.as_mut().unwrap();
        input.write_all(&(bytes.len() as u32).to_le_bytes()).unwrap();input.write_all(&bytes).unwrap();input.flush().unwrap();
        let response=self.read();std::fs::write(self.folder.join(format!("response-{id}.json")),serde_json::to_vec(&response).unwrap()).unwrap();
        if response["kind"]!="closed" {
            assert_eq!(response["id"],id);
            for field in ["user_us","system_us"] {assert!(response["cpu_after"][field].as_u64().unwrap()>=response["cpu_before"][field].as_u64().unwrap());}
        }
        response
    }
    fn close(&mut self) {
        let result=self.send(json!({"command":"shutdown"}));assert_eq!(result["kind"],"closed");
        drop(self.input.take());let status=self.child.wait().unwrap();assert!(status.success());
        std::fs::write(self.folder.join("terminal.json"),serde_json::to_vec(&json!({"returncode":status.code(),"closed":result})).unwrap()).unwrap();
    }
}

#[path="template_session_socket/support.rs"]
mod socket;
impl Drop for Session {fn drop(&mut self) {drop(self.input.take());let _=self.child.wait();}}

fn inputs(folder:&Path,label:&str,value:u128,data:u8)->(Value,Value) {
    let function=|name:&str,code:Vec<Op>|Function{name:name.into(),frame_size:8,frame_align:8,registers:4,args:vec![],result:Slot{offset:0,size:0},code};
    let mut functions=vec![function("batch",vec![Op::Return])];
    for i in 0..32 {functions.push(function(&format!("test{i}"),vec![Op::Local{dst:0,offset:0},Op::Call{function:33,args:vec![],destination:0},
        Op::Load{dst:1,address:0,size:8},Op::Assert{value:1,expected:true,message:"current callee".into()},
        Op::Imm{dst:0,value:8},Op::Load{dst:1,address:0,size:1},Op::Assert{value:1,expected:true,message:"current data".into()},
        Op::Imm{dst:0,value:16},Op::EnvironmentGet{dst:1,name:0},Op::Load{dst:2,address:1,size:1},
        Op::Assert{value:2,expected:true,message:"current environment".into()},Op::Return]));}
    let mut callee=function("callee",vec![Op::Local{dst:0,offset:0},Op::Imm{dst:1,value},Op::Store{address:0,src:1,size:8},Op::Return]);
    callee.result.size=8;functions.push(callee);
    let mut bytes=vec![0;16];bytes[8]=data;bytes.extend_from_slice(b"SESSION_VALUE\0");
    let program=Program{version:VERSION,target:"aarch64-apple-darwin".into(),entry:0,data:bytes,statics:vec![],thread_locals:vec![],functions};
    let artifact=bincode::serialize(&program).unwrap();let artifact_hash=digest(&artifact);
    let entries=(1..=32).map(|function|SelectedEntry{name:format!("test{function}"),function,body_name:program.functions[function].name.clone()}).collect();
    let catalog=serde_json::to_vec(&EntryCatalog::new(&program,artifact_hash.clone(),entries).unwrap()).unwrap();
    let a=folder.join(format!("{label}.rbc"));let c=folder.join(format!("{label}.catalog.json"));
    std::fs::write(&a,&artifact).unwrap();std::fs::write(&c,&catalog).unwrap();
    (json!({"path":a,"sha256":artifact_hash}),json!({"path":c,"sha256":digest(&catalog)}))
}
fn request(session:&Session,label:&str,value:u128,data:u8,env:&[u8])->Value {
    let (artifact,catalog)=inputs(&session.folder,label,value,data);
    json!({"command":"run","artifact":artifact,"catalog":catalog,"report":session.folder.join(format!("{label}.report.json")),
        "cwd":std::env::current_dir().unwrap(),"environment":[[b"SESSION_VALUE".to_vec(),env]],
        "budget":{"instructions":100_000,"allocations":1000,"memory_bytes":1024*1024,"frames":64,"code_bytes":16*1024*1024,
            "persistent_registers":true,"scalar_calls":true}})
}

#[test]
fn edited_suites_and_request_inputs_match_without_and_with_history() {
    let mut reference=vec![];
    for (label,history) in [("fresh",0),("cached",64*1024*1024)] {
        let mut session=Session::start(label,history);let mut hits=0;
        for (i,(value,data,env,passed)) in [(7,1,&b"yes"[..],true),(8,1,&b""[..],false),(8,1,&b"yes"[..],true),
            (0,1,&b"yes"[..],false),(7,0,&b"yes"[..],false),(7,1,&b"yes"[..],true)].into_iter().enumerate() {
            let request=request(&session,&format!("case{i}"),value,data,env);let response=session.send(request);
            assert_eq!(response["kind"],"result");assert_eq!(response["status"],if passed {"passed"} else {"failed"});
            let bytes=std::fs::read(response["report"].as_str().unwrap()).unwrap();assert_eq!(response["report_sha256"],digest(&bytes));
            let report:Value=serde_json::from_slice(&bytes).unwrap();assert_eq!(report["completed"],32);assert_eq!(report["selected"],32);
            assert_eq!(report["passed"],if passed {32} else {0});assert_eq!(report["failed"],if passed {0} else {32});
            let outcomes=report["tests"].as_array().unwrap().iter().map(|t|(t["name"].clone(),t["status"].clone(),t["error"].clone())).collect::<Vec<_>>();
            if history==0 {reference.push(outcomes);} else {assert_eq!(outcomes,reference[i]);}
            #[cfg(feature = "jit-preparation-observer")]
            {
                let input=&report["input_observer"];
                let sum=["artifact_read_hash_ns","artifact_decode_ns","catalog_read_hash_ns","catalog_decode_ns",
                    "catalog_validation_ns","program_validation_ns","report_reservation_ns"].iter()
                    .map(|field|input[*field].as_u64().unwrap()).sum::<u64>();
                assert_eq!(sum,input["total_ns"].as_u64().unwrap());
                assert!(input["artifact_bytes"].as_u64().unwrap()>0 && input["catalog_bytes"].as_u64().unwrap()>0);
                let output=&response["output_observer"];
                assert_eq!(["serialization_ns","write_flush_ns","digest_ns"].iter()
                    .map(|field|output[*field].as_u64().unwrap()).sum::<u64>(),output["total_ns"].as_u64().unwrap());
                assert_eq!(output["report_bytes"],bytes.len());
                assert!((sum+output["total_ns"].as_u64().unwrap()) as f64 <= response["request_seconds"].as_f64().unwrap()*1e9);
            }
            #[cfg(not(feature = "jit-preparation-observer"))]
            {assert!(report.get("input_observer").is_none() && response.get("output_observer").is_none());}
            for row in report["worker_records"].as_array().unwrap() {
                #[cfg(feature = "jit-preparation-observer")]
                {
                    let setup=&row["preparation_observer"]["constructor"];
                    assert_eq!(setup["total_ns"],row["preparation_ns"]);
                    assert!(setup["before_metadata_ns"].as_u64().unwrap()+setup["execution_metadata_ns"].as_u64().unwrap()
                        <=setup["total_ns"].as_u64().unwrap());
                }
                if history==0 {assert!(row["templates"].is_null() && row["storage"].is_null());}
                else {let n=row["templates"]["hits"].as_u64().unwrap();hits+=n;assert_eq!(row["templates"]["verified_hits"],n);
                    assert!(row["storage"]["charged_bytes"].as_u64().unwrap()<=history as u64);}
            }
        }
        if history>0 {assert!(hits>0);}session.close();
    }
}

#[test]
fn rejected_inputs_and_existing_reports_do_not_poison_the_next_request() {
    let mut session=Session::start("rejections",1024*1024);
    for case in 0..4 {
        let mut body=request(&session,&format!("bad{case}"),7,1,b"ok");let path=PathBuf::from(body["report"].as_str().unwrap());
        match case {
            0=>body["artifact"]["sha256"]="0".repeat(64).into(),
            1=>body["cwd"]="/different-session-directory".into(),
            2=>{std::fs::write(&path,b"preserve existing report").unwrap();},
            _=>body["budget"]["allocations"]=1_000_001.into(),
        }
        let response=session.send(body);assert_eq!(response["kind"],"error");assert_eq!(response["poisoned"],false);
        if case==2 {assert_eq!(std::fs::read(&path).unwrap(),b"preserve existing report");} else {assert!(!path.exists());}
    }
    let body=request(&session,"valid",7,1,b"ok");assert_eq!(session.send(body)["status"],"passed");session.close();
}

#[test]
fn malformed_frames_close_only_the_owned_session_without_execution() {
    let mut session=Session::start("malformed",0);
    session.input.as_mut().unwrap().write_all(&0u32.to_le_bytes()).unwrap();session.input.as_mut().unwrap().flush().unwrap();
    drop(session.input.take());let status=session.child.wait().unwrap();assert!(!status.success());
    let mut bytes=vec![];session.output.read_to_end(&mut bytes).unwrap();assert!(bytes.is_empty());
    std::fs::write(session.folder.join("terminal.json"),serde_json::to_vec(&json!({"returncode":status.code(),"expected_protocol_rejection":true})).unwrap()).unwrap();
}
