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
