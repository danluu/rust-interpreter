use super::*;
use std::os::unix::{fs::PermissionsExt,net::UnixStream};

fn endpoint(label:&str)->PathBuf {
    let base=std::env::var_os("RUST_INTERP_SOCKET_FIXTURES").map(PathBuf::from).unwrap_or_else(std::env::temp_dir);
    base.canonicalize().unwrap().join(format!("ts-{}-{label}",std::process::id()))
}
fn read(stream:&mut impl Read)->Value {
    let mut length=[0;4];stream.read_exact(&mut length).unwrap();let n=u32::from_le_bytes(length) as usize;
    assert!(n>0 && n<=4*1024*1024);let mut bytes=vec![0;n];stream.read_exact(&mut bytes).unwrap();serde_json::from_slice(&bytes).unwrap()
}
fn write(stream:&mut impl Write,value:&Value) {
    let bytes=serde_json::to_vec(value).unwrap();stream.write_all(&(bytes.len() as u32).to_le_bytes()).unwrap();
    stream.write_all(&bytes).unwrap();stream.flush().unwrap();
}
struct Socket {session:Session,private:Value}
impl Socket {
    fn start(label:&str,history:usize)->Self {
        let path=endpoint(label);
        let args=["--serve-socket".into(),path.to_str().unwrap().into(),"--history-bytes".into(),history.to_string(),"--verify-hits".into()];
        let mut session=Session::launch(label,&args);session.initialize();
        assert!(session.ready.get("auth").is_none());
        let private:Value=serde_json::from_slice(&std::fs::read(path.join("ready.json")).unwrap()).unwrap();
        assert_eq!(private["pid"],session.child.id());
        for (file,mode) in [(path.clone(),0o700),(path.join("ready.json"),0o600),(path.join("socket"),0o600)] {
            assert_eq!(std::fs::symlink_metadata(file).unwrap().permissions().mode()&0o777,mode);
        }
        Self{session,private}
    }
    fn connect(&self)->(UnixStream,Value) {
        let mut stream=UnixStream::connect(self.private["socket"].as_str().unwrap()).unwrap();
        stream.set_read_timeout(Some(std::time::Duration::from_secs(30))).unwrap();
        stream.set_write_timeout(Some(std::time::Duration::from_secs(30))).unwrap();
        let greeting=read(&mut stream);assert_eq!(greeting["kind"],"greeting");
        assert_eq!(greeting["pid"],self.session.child.id());assert_eq!(greeting["executable_sha256"],self.private["executable_sha256"]);
        (stream,greeting)
    }
    fn envelope(&self,id:u64,body:Value)->Value {
        json!({"auth":self.private["auth"],"executable_sha256":self.private["executable_sha256"],
            "request":{"schema":1,"id":id,"body":body}})
    }
    fn send(&self,body:Value)->Value {
        let (mut stream,greeting)=self.connect();let id=greeting["next_id"].as_u64().unwrap();
        write(&mut stream,&self.envelope(id,body));let response=read(&mut stream);
        assert_eq!(response["id"],id);assert_eq!(response["pid"],self.session.child.id());
        assert_eq!(response["executable_sha256"],self.private["executable_sha256"]);
        assert!(!serde_json::to_string(&response).unwrap().contains(self.private["auth"].as_str().unwrap()));
        std::fs::write(self.session.folder.join(format!("response-{id}.json")),serde_json::to_vec(&response).unwrap()).unwrap();response
    }
    fn close(&mut self) {
        let response=self.send(json!({"command":"shutdown"}));assert_eq!(response["kind"],"closed");
        assert_eq!(self.session.read(),response);drop(self.session.input.take());let status=self.session.child.wait().unwrap();assert!(status.success());
        std::fs::write(self.session.folder.join("terminal.json"),serde_json::to_vec(&json!({"returncode":status.code(),"closed":response})).unwrap()).unwrap();
    }
}

#[test]
fn socket_edits_keep_current_inputs_and_verified_history() {
    let mut reference=vec![];
    for (label,history) in [("socket-fresh",0),("socket-cached",64*1024*1024)] {
        let mut socket=Socket::start(label,history);let mut hits=0;
        for (i,(value,data,env,passed)) in [(7,1,&b"yes"[..],true),(8,1,&b""[..],false),(8,1,&b"yes"[..],true),
            (0,1,&b"yes"[..],false),(7,0,&b"yes"[..],false),(7,1,&b"yes"[..],true)].into_iter().enumerate() {
            let body=request(&socket.session,&format!("case{i}"),value,data,env);let response=socket.send(body);
            assert_eq!(response["kind"],"result");assert_eq!(response["status"],if passed {"passed"} else {"failed"});
            let bytes=std::fs::read(response["report"].as_str().unwrap()).unwrap();assert_eq!(response["report_sha256"],digest(&bytes));
            let report:Value=serde_json::from_slice(&bytes).unwrap();assert_eq!(report["completed"],32);assert_eq!(report["selected"],32);
            assert_eq!(report["passed"],if passed {32} else {0});assert_eq!(report["failed"],if passed {0} else {32});
            let outcomes=report["tests"].as_array().unwrap().iter().map(|t|(t["name"].clone(),t["status"].clone(),t["error"].clone())).collect::<Vec<_>>();
            if history==0 {reference.push(outcomes);} else {assert_eq!(outcomes,reference[i]);}
            for row in report["worker_records"].as_array().unwrap() {
                if history==0 {assert!(row["templates"].is_null() && row["storage"].is_null());}
                else {let n=row["templates"]["hits"].as_u64().unwrap();hits+=n;assert_eq!(row["templates"]["verified_hits"],n);
                    assert!(row["storage"]["charged_bytes"].as_u64().unwrap()<=history as u64);}
            }
        }
        if history>0 {assert!(hits>0);}socket.close();
    }
}

#[test]
fn socket_rejects_bad_connections_and_never_replays_a_lost_response() {
    let mut socket=Socket::start("socket-rejections",1024*1024);
    for case in 0..8 {
        let (mut stream,greeting)=socket.connect();assert_eq!(greeting["next_id"],1);
        let mut envelope=socket.envelope(1,json!({"command":"shutdown"}));
        match case {
            0=>envelope["auth"]="0".repeat(64).into(),
            1=>envelope["executable_sha256"]="0".repeat(64).into(),
            2=>envelope["request"]["schema"]=2.into(),
            3=>envelope["request"]["id"]=2.into(),
            4=>envelope["extra"]=true.into(),
            5=>envelope["request"]["body"]["extra"]=true.into(),
            6=>envelope["request"]["extra"]=true.into(),
            _=>{},
        }
        if case==7 {stream.write_all(&0u32.to_le_bytes()).unwrap();} else {write(&mut stream,&envelope);}
        let rejected=read(&mut stream);assert_eq!(rejected["kind"],"rejected");assert_eq!(rejected["execution_possible"],false);
        std::fs::write(socket.session.folder.join(format!("rejected-{case}.json")),serde_json::to_vec(&rejected).unwrap()).unwrap();
    }
    for case in 0..2 {
        let mut body=request(&socket.session,&format!("invalid{case}"),7,1,b"yes");let report=PathBuf::from(body["report"].as_str().unwrap());
        if case==0 {body["cwd"]="/wrong-session-cwd".into();} else {std::fs::write(&report,b"existing report").unwrap();}
        let response=socket.send(body);assert_eq!(response["kind"],"error");assert_eq!(response["poisoned"],false);
        if case==0 {assert!(!report.exists());} else {assert_eq!(std::fs::read(&report).unwrap(),b"existing report");}
    }
    let body=request(&socket.session,"lost",7,1,b"yes");let report=PathBuf::from(body["report"].as_str().unwrap());
    let (mut stream,greeting)=socket.connect();assert_eq!(greeting["next_id"],3);
    write(&mut stream,&socket.envelope(3,body.clone()));drop(stream);
    // The next greeting is sent only after the accepted request has completed.
    let (stream,greeting)=socket.connect();assert_eq!(greeting["next_id"],4);drop(stream);
    let retained=std::fs::read(&report).unwrap();let result:Value=serde_json::from_slice(&retained).unwrap();assert_eq!(result["passed"],32);
    // An explicit resubmission cannot overwrite the reserved outcome or execute again.
    assert_eq!(socket.send(body)["kind"],"error");assert_eq!(std::fs::read(&report).unwrap(),retained);
    let body=request(&socket.session,"valid",7,1,b"yes");assert_eq!(socket.send(body)["status"],"passed");socket.close();
}

#[test]
fn socket_owner_eof_joins_workers_and_preserves_endpoint() {
    let mut socket=Socket::start("socket-owner-eof",1024*1024);drop(socket.session.input.take());
    let closed=socket.session.read();assert_eq!(closed["reason"],"owner_eof");assert_eq!(closed["requests_consumed"],0);
    let status=socket.session.child.wait().unwrap();assert!(status.success());
    assert!(Path::new(socket.private["ready_path"].as_str().unwrap()).exists());
    assert!(UnixStream::connect(socket.private["socket"].as_str().unwrap()).is_err());
    std::fs::write(socket.session.folder.join("terminal.json"),serde_json::to_vec(&json!({"returncode":status.code(),"closed":closed})).unwrap()).unwrap();
}

#[test]
fn socket_start_refuses_an_existing_endpoint_directory() {
    let path=endpoint("occupied");std::fs::create_dir(&path).unwrap();std::fs::write(path.join("marker"),b"preserved").unwrap();
    let args=["--serve-socket".into(),path.to_str().unwrap().into(),"--history-bytes".into(),"0".into()];
    let mut session=Session::launch("socket-occupied",&args);drop(session.input.take());
    let status=session.child.wait().unwrap();assert_eq!(status.code(),Some(1));let mut output=vec![];session.output.read_to_end(&mut output).unwrap();
    assert!(output.is_empty());assert_eq!(std::fs::read(path.join("marker")).unwrap(),b"preserved");assert!(!path.join("socket").exists());
    std::fs::write(session.folder.join("terminal.json"),serde_json::to_vec(&json!({"returncode":status.code(),"expected_existing_directory_rejection":true})).unwrap()).unwrap();
}

fn client(socket:&Socket,label:&str,body:&Value,env:&str,extra:&[&str])->std::process::Output {
    let executable=env!("CARGO_BIN_EXE_rust-interp-vm");
    let mut args=vec!["--jit-template-session",socket.private["ready_path"].as_str().unwrap(),"--engine","jit",
        "--jit-resumable-calls","--jit-scalar-calls","--jit-persistent-registers","--isolated-batch","prepared",
        "--suite-workers","2","--suite-catalog",body["catalog"]["path"].as_str().unwrap(),
        "--suite-report",body["report"].as_str().unwrap(),"--instruction-limit","100000","--allocation-limit","1000"];
    args.extend_from_slice(extra);args.push(body["artifact"]["path"].as_str().unwrap());
    let child=Command::new(executable).args(&args).env("SESSION_VALUE",env).stdin(Stdio::null()).stdout(Stdio::piped()).stderr(Stdio::piped()).spawn().unwrap();
    let mut receipt=json!({"pid":child.id(),"parent_pid":std::process::id(),"executable":executable,
        "executable_sha256":digest(&std::fs::read(executable).unwrap()),"args":args,"cwd":std::env::current_dir().unwrap(),
        "started_epoch":std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64()});
    let prefix=socket.session.folder.join(format!("client-{label}"));
    std::fs::write(prefix.with_extension("json"),serde_json::to_vec(&receipt).unwrap()).unwrap();
    let output=child.wait_with_output().unwrap();receipt["returncode"]=output.status.code().into();
    std::fs::write(prefix.with_extension("json"),serde_json::to_vec(&receipt).unwrap()).unwrap();
    std::fs::write(prefix.with_extension("stdout"),&output.stdout).unwrap();std::fs::write(prefix.with_extension("stderr"),&output.stderr).unwrap();
    output
}

#[test]
fn vm_client_preserves_changed_inputs_and_actual_server_identity() {
    let mut socket=Socket::start("vm-client-edits",64*1024*1024);let mut hits=0;
    for (i,(value,data,env,passed)) in [(7,1,"yes",true),(8,1,"",false),(8,1,"yes",true),
        (0,1,"yes",false),(7,0,"yes",false),(7,1,"yes",true)].into_iter().enumerate() {
        let label=format!("edit{i}");let body=request(&socket.session,&label,value,data,b"unused");
        let output=client(&socket,&label,&body,env,&[]);assert_eq!(output.status.success(),passed,"{}",String::from_utf8_lossy(&output.stderr));
        let path=body["report"].as_str().unwrap();let bytes=std::fs::read(path).unwrap();
        let report:Value=serde_json::from_slice(&bytes).unwrap();let receipt:Value=serde_json::from_slice(&std::fs::read(format!("{path}.session.json")).unwrap()).unwrap();
        assert_eq!(receipt["status"],"completed");assert_eq!(receipt["server_pid"],socket.session.child.id());
        assert_eq!(receipt["server_executable_sha256"],socket.private["executable_sha256"]);assert_eq!(receipt["report_sha256"],digest(&bytes));
        assert_eq!(report["completed"],32);assert_eq!(report["passed"],if passed {32} else {0});
        assert_eq!(report["request_id"],i+1);
        for worker in report["worker_records"].as_array().unwrap() {
            let n=worker["templates"]["hits"].as_u64().unwrap();assert_eq!(worker["templates"]["verified_hits"],n);hits+=n;
        }
        assert!(!serde_json::to_string(&receipt).unwrap().contains(socket.private["auth"].as_str().unwrap()));
    }
    assert!(hits>0);socket.close();
}

#[test]
fn vm_client_rejects_options_stale_identity_and_reserved_outputs_without_fallback() {
    let mut socket=Socket::start("vm-client-reject",0);
    for (i,extra) in [vec!["--guest-getcwd"],vec!["--guest-descriptor-io"],vec!["--jit-native-calls"],vec!["--suite-workers","1"]].iter().enumerate() {
        let label=format!("option{i}");let body=request(&socket.session,&label,7,1,b"unused");
        assert!(!client(&socket,&label,&body,"yes",extra).status.success());assert!(!Path::new(body["report"].as_str().unwrap()).exists());
    }
    let ready_path=PathBuf::from(socket.private["ready_path"].as_str().unwrap());let original=std::fs::read(&ready_path).unwrap();
    for case in 0..2 {
        let label=format!("identity{case}");let body=request(&socket.session,&label,7,1,b"unused");
        if case==0 {let mut changed=socket.private.clone();changed["executable_sha256"]="0".repeat(64).into();
            std::fs::write(&ready_path,serde_json::to_vec(&changed).unwrap()).unwrap();}
        else {std::fs::set_permissions(&ready_path,std::fs::Permissions::from_mode(0o644)).unwrap();}
        let output=client(&socket,&label,&body,"yes",&[]);
        std::fs::write(&ready_path,&original).unwrap();std::fs::set_permissions(&ready_path,std::fs::Permissions::from_mode(0o600)).unwrap();
        assert!(!output.status.success());assert!(!Path::new(body["report"].as_str().unwrap()).exists());
    }
    for case in 0..2 {
        let label=format!("reserved{case}");let body=request(&socket.session,&label,7,1,b"unused");let report=body["report"].as_str().unwrap();
        let occupied=if case==0 {report.to_owned()} else {format!("{report}.session.json")};std::fs::write(&occupied,b"reserved").unwrap();
        assert!(!client(&socket,&label,&body,"yes",&[]).status.success());assert_eq!(std::fs::read(occupied).unwrap(),b"reserved");
    }
    let (stream,greeting)=socket.connect();assert_eq!(greeting["next_id"],1);drop(stream);
    let body=request(&socket.session,"malformed-artifact",7,1,b"unused");std::fs::write(body["artifact"]["path"].as_str().unwrap(),b"invalid").unwrap();
    assert!(!client(&socket,"malformed-artifact",&body,"yes",&[]).status.success());assert!(!Path::new(body["report"].as_str().unwrap()).exists());
    let body=request(&socket.session,"recovered",7,1,b"unused");assert!(client(&socket,"recovered",&body,"yes",&[]).status.success());
    let report:Value=serde_json::from_slice(&std::fs::read(body["report"].as_str().unwrap()).unwrap()).unwrap();assert_eq!(report["request_id"],2);
    socket.close();
}

#[test]
fn vm_client_catalog_declarations_never_replace_server_input_validation() {
    let mut socket=Socket::start("vm-client-bindings",1024*1024);
    let mut expected_id=1;
    for case in 0..6 {
        let label=format!("binding{case}");let body=request(&socket.session,&label,7,1,b"unused");
        let artifact=Path::new(body["artifact"]["path"].as_str().unwrap());
        let catalog=Path::new(body["catalog"]["path"].as_str().unwrap());
        let mut declared:Value=serde_json::from_slice(&std::fs::read(catalog).unwrap()).unwrap();
        match case {
            0=>{
                let (changed,_)=inputs(&socket.session.folder,"changed-artifact",8,1);
                std::fs::write(artifact,std::fs::read(changed["path"].as_str().unwrap()).unwrap()).unwrap();
            },
            1=>declared["artifact_sha256"]="malformed digest".into(),
            2=>declared["bytecode_version"]=0.into(),
            3|5=>{
                let mut program:Program=bincode::deserialize(&std::fs::read(artifact).unwrap()).unwrap();
                if case==3 {program.functions[1].registers=0;} else {program.version|=rust_interp_bytecode::PARTIAL_VALIDATION;}
                let bytes=bincode::serialize(&program).unwrap();declared["artifact_sha256"]=digest(&bytes).into();
                if case==5 {declared["bytecode_version"]=program.version.into();}
                std::fs::write(artifact,bytes).unwrap();
            },
            _=>{
                let mut bytes=std::fs::read(artifact).unwrap();bytes.push(0);
                declared["artifact_sha256"]=digest(&bytes).into();std::fs::write(artifact,bytes).unwrap();
            },
        }
        std::fs::write(catalog,serde_json::to_vec(&declared).unwrap()).unwrap();
        let output=client(&socket,&label,&body,"yes",&[]);assert!(!output.status.success());
        let report=body["report"].as_str().unwrap();assert!(!Path::new(report).exists());
        if case==1 {assert!(!Path::new(&format!("{report}.session.json")).exists());}
        else {
            expected_id+=1;
            let receipt:Value=serde_json::from_slice(&std::fs::read(format!("{report}.session.json")).unwrap()).unwrap();
            assert_eq!(receipt["status"],"unknown-or-error");assert_eq!(receipt["response"]["kind"],"error");
        }
        let (stream,greeting)=socket.connect();assert_eq!(greeting["next_id"],expected_id);drop(stream);
    }
    let body=request(&socket.session,"binding-recovery",7,1,b"unused");
    assert!(client(&socket,"binding-recovery",&body,"yes",&[]).status.success());socket.close();
}
