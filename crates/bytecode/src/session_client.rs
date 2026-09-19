//! Explicit one-shot client; never starts a server or retries a guest request.
use rust_interp_bytecode::Limits;
use serde_json::{Value,json};
use sha2::{Digest,Sha256};
use std::{io::{Read,Write,Seek,SeekFrom},path::{Path,PathBuf},os::unix::{ffi::OsStrExt,fs::MetadataExt,net::UnixStream}};

const MAX_FRAME:usize=4*1024*1024;
fn digest(bytes:&[u8])->String {format!("{:x}",Sha256::digest(bytes))}
fn hex(value:&Value)->bool {value.as_str().is_some_and(|s|s.len()==64 && s.bytes().all(|b|b.is_ascii_digit() || (b'a'..=b'f').contains(&b)))}
fn read_bound(path:&Path,limit:usize)->Result<Vec<u8>,String> {
    let file=std::fs::File::open(path).map_err(|e|e.to_string())?;let metadata=file.metadata().map_err(|e|e.to_string())?;
    if !metadata.is_file() || metadata.len()>limit as u64 {return Err("session input is not a bounded regular file".into());}
    let mut bytes=vec![];file.take(limit as u64+1).read_to_end(&mut bytes).map_err(|e|e.to_string())?;
    if bytes.len()>limit {return Err("session input grew beyond its bound".into());}Ok(bytes)
}
fn read_frame(stream:&mut UnixStream)->Result<Value,String> {
    let mut length=[0;4];stream.read_exact(&mut length).map_err(|e|e.to_string())?;
    let length=u32::from_le_bytes(length) as usize;if !(1..=MAX_FRAME).contains(&length) {return Err("invalid session frame length".into());}
    let mut bytes=vec![0;length];stream.read_exact(&mut bytes).map_err(|e|e.to_string())?;
    serde_json::from_slice(&bytes).map_err(|e|e.to_string())
}
fn persist(file:&mut std::fs::File,value:&Value)->Result<(),String> {
    let bytes=serde_json::to_vec(value).map_err(|e|e.to_string())?;
    if bytes.len()>MAX_FRAME {return Err("session receipt exceeds bound".into());}
    file.seek(SeekFrom::Start(0)).and_then(|_|file.write_all(&bytes)).and_then(|_|file.set_len(bytes.len() as u64))
        .and_then(|_|file.flush()).map_err(|e|e.to_string())
}
fn input_path(path:&str)->Result<PathBuf,String> {
    let path=Path::new(path).canonicalize().map_err(|e|e.to_string())?;
    if path.as_os_str().len()>4096 {return Err("session input path exceeds bound".into());}
    Ok(path)
}
fn input_bindings(artifact:&str,catalog:&str)->Result<(Value,Value),String> {
    let artifact=input_path(artifact)?;let catalog=input_path(catalog)?;
    let bytes=read_bound(&catalog,MAX_FRAME)?;
    let declared:rust_interp_bytecode::EntryCatalog=serde_json::from_slice(&bytes).map_err(|e|e.to_string())?;
    // The server reads/hashes the actual bytes, checks this declaration against
    // them and validates the complete Program before any guest can execute.
    Ok((json!({"path":artifact,"sha256":declared.declared_artifact_sha256()?}),
        json!({"path":catalog,"sha256":digest(&bytes)})))
}
fn new_report(path:&str)->Result<PathBuf,String> {
    let cwd=std::env::current_dir().map_err(|e|e.to_string())?;let path=cwd.join(path);
    let name=path.file_name().ok_or("missing report name")?;
    let parent=path.parent().ok_or("missing report parent")?.canonicalize().map_err(|e|e.to_string())?;
    let path=parent.join(name);
    if path.as_os_str().len()>4096 {return Err("session report path exceeds bound".into());}
    match path.symlink_metadata() {
        Err(e) if e.kind()==std::io::ErrorKind::NotFound=>Ok(path),
        _=>Err("session report already exists or is inaccessible".into()),
    }
}
fn private_readiness(path:&str)->Result<(Value,String),String> {
    let path=Path::new(path);
    if !path.is_absolute() || path.as_os_str().len()>4096 || path.canonicalize().map_err(|e|e.to_string())?!=path {
        return Err("session readiness requires a canonical absolute path".into());
    }
    let parent=path.parent().ok_or("missing session directory")?;
    let dir=parent.symlink_metadata().map_err(|e|e.to_string())?;let file=path.symlink_metadata().map_err(|e|e.to_string())?;
    // POSIX effective user ID; the private capability may only leave its owner.
    unsafe extern "C" {fn geteuid()->u32;}
    let uid=unsafe {geteuid()};
    if !dir.is_dir() || dir.mode()&0o777!=0o700 || dir.uid()!=uid
        || !file.is_file() || file.mode()&0o777!=0o600 || file.uid()!=uid {
        return Err("session readiness and directory must be private and owned by this user".into());
    }
    let bytes=read_bound(path,16*1024)?;let ready:Value=serde_json::from_slice(&bytes).map_err(|e|e.to_string())?;
    let socket=parent.join("socket");let metadata=socket.symlink_metadata().map_err(|e|e.to_string())?;
    use std::os::unix::fs::FileTypeExt;
    if !metadata.file_type().is_socket() || metadata.mode()&0o777!=0o600 || metadata.uid()!=uid
        || ready["kind"]!="ready" || ready["schema"]!=1 || ready["workers"]!=2 || !hex(&ready["auth"])
        || !hex(&ready["executable_sha256"]) || ready["pid"].as_u64().is_none_or(|pid|pid==0 || pid>i32::MAX as u64)
        || ready["socket"]!=socket.to_string_lossy().as_ref() || ready["ready_path"]!=path.to_string_lossy().as_ref()
        || ready["verify_hits"].as_bool().is_none() || ready["history_bytes_per_worker"].as_u64().is_none_or(|n|n>64*1024*1024 || (n>0 && n<512)) {
        return Err("session readiness identity or endpoint differs".into());
    }
    Ok((ready,digest(&bytes)))
}

pub(super) fn run(ready_path:&str,artifact:&str,catalog:&str,report:&str,limits:&Limits)->Result<(),String> {
    let (ready,ready_hash)=private_readiness(ready_path)?;
    let cwd=std::env::current_dir().map_err(|e|e.to_string())?;
    if ready["cwd"]!=cwd.to_string_lossy().as_ref() {return Err("session working directory differs".into());}
    if limits.jit_indirect_calls && ready["indirect_calls"]!=true {
        return Err("session server does not support indirect calls; no request sent".into());
    }
    let options=json!({"persistent_registers":limits.jit_persistent_registers,"scalar_calls":limits.jit_scalar_calls,"indirect_calls":limits.jit_indirect_calls});
    let (artifact,catalog)=input_bindings(artifact,catalog)?;let report=new_report(report)?;
    let mut environment=Vec::new();let mut charged=0usize;
    for (key,value) in std::env::vars_os() {
        let key=key.as_bytes().to_vec();let value=value.as_bytes().to_vec();
        charged=charged.checked_add(key.len()).and_then(|n|n.checked_add(value.len())).and_then(|n|n.checked_add(128)).ok_or("environment size overflow")?;
        if environment.len()>=4096 || charged>1024*1024 || key.contains(&0) || value.contains(&0) {return Err("session environment exceeds bound".into());}
        environment.push((key,value));
    }
    let mut body=json!({"command":"run","artifact":artifact,"catalog":catalog,"report":report,"cwd":cwd,"environment":environment,
        "budget":{"instructions":limits.instructions,"allocations":limits.allocations,"memory_bytes":limits.memory,
            "frames":limits.frames,"code_bytes":limits.jit_code_bytes,"persistent_registers":limits.jit_persistent_registers,"scalar_calls":limits.jit_scalar_calls}});
    if ready["indirect_calls"]==true {body["budget"]["indirect_calls"]=limits.jit_indirect_calls.into();}
    let mut stream=UnixStream::connect(ready["socket"].as_str().unwrap()).map_err(|e|e.to_string())?;
    stream.set_read_timeout(Some(std::time::Duration::from_secs(30))).map_err(|e|e.to_string())?;
    stream.set_write_timeout(Some(std::time::Duration::from_secs(30))).map_err(|e|e.to_string())?;
    let greeting=read_frame(&mut stream)?;
    if greeting["kind"]!="greeting" || greeting["schema"]!=1 || greeting["pid"]!=ready["pid"]
        || greeting["executable_sha256"]!=ready["executable_sha256"] || greeting["next_id"].as_u64().is_none_or(|id|!(1..=4096).contains(&id)) {
        return Err("session greeting identity or sequence differs; no request sent".into());
    }
    let id=greeting["next_id"].as_u64().unwrap();
    let bytes=serde_json::to_vec(&json!({"auth":ready["auth"],"executable_sha256":ready["executable_sha256"],
        "request":{"schema":1,"id":id,"body":body}})).map_err(|e|e.to_string())?;
    if bytes.len()>MAX_FRAME {return Err("session request exceeds frame bound".into());}
    let receipt_path=PathBuf::from(format!("{}.session.json",report.display()));
    let mut file=std::fs::OpenOptions::new().write(true).create_new(true).open(&receipt_path).map_err(|e|e.to_string())?;
    let mut receipt=json!({"schema_version":1,"transport":"private-unix-socket","request_id":id,
        "server_pid":ready["pid"],"server_executable_sha256":ready["executable_sha256"],"readiness_sha256":ready_hash,
        "history_bytes_per_worker":ready["history_bytes_per_worker"],"verify_hits":ready["verify_hits"],"cpu_at_ready":ready["cpu_at_ready"],
        "artifact_sha256":artifact["sha256"],"catalog_sha256":catalog["sha256"],"report":report,
        "status":"sending","execution_possible":true});
    persist(&mut file,&receipt)?;
    let exchange=(||->Result<(),String>{
        stream.write_all(&(bytes.len() as u32).to_le_bytes()).and_then(|_|stream.write_all(&bytes)).map_err(|e|e.to_string())?;
        let response=read_frame(&mut stream)?;
        if response["id"]!=id || response["pid"]!=ready["pid"] || response["executable_sha256"]!=ready["executable_sha256"] {
            return Err("session response identity differs; outcome is unknown".into());
        }
        receipt["response"]=response.clone();
        if response["kind"]!="result" || response["poisoned"]!=false || response["report"]!=report.to_string_lossy().as_ref() || !hex(&response["report_sha256"]) {
            return Err("session did not return a complete suite result; inspect the retained receipt".into());
        }
        for field in ["user_us","system_us"] {
            let start=ready["cpu_at_ready"][field].as_u64().ok_or("missing session ready CPU counter")?;
            let before=response["cpu_before"][field].as_u64().ok_or("missing session entry CPU counter")?;
            let after=response["cpu_after"][field].as_u64().ok_or("missing session exit CPU counter")?;
            if start>before || before>after {return Err("session CPU counters decreased".into());}
        }
        let bytes=read_bound(&report,MAX_FRAME)?;
        if response["report_sha256"]!=digest(&bytes) {return Err("session report hash differs".into());}
        let result:Value=serde_json::from_slice(&bytes).map_err(|e|e.to_string())?;
        if result["request_id"]!=id || result["artifact_sha256"]!=artifact["sha256"] || result["catalog_sha256"]!=catalog["sha256"]
            || result["completed"]!=result["selected"] || result["status"]!=response["status"] || result["schema_version"]!=1
            || result["mode"]!="prepared" || result["workers"]!=2 || result["poisoned"]!=false
            || result["runtime_limits"]!=json!({"instructions":limits.instructions,"allocations":limits.allocations,"memory_bytes":limits.memory,"frames":limits.frames})
            || result["jit_code_limit_bytes"]!=limits.jit_code_bytes
            || ready["indirect_calls"]==true && result["jit_options"]!=options {
            return Err("session report identity or coverage differs".into());
        }
        let tests=result["tests"].as_array().ok_or("missing session test outcomes")?;
        let failed=tests.iter().filter(|t|t["status"]=="failed").count();
        if tests.is_empty() || result["selected"]!=tests.len() || result["passed"]!=tests.len()-failed || result["failed"]!=failed
            || result["status"]!=if failed==0 {"passed"} else {"failed"}
            || !tests.iter().enumerate().all(|(i,t)|t["index"]==i && (t["status"]=="passed" || t["status"]=="failed")) {
            return Err("session test outcome coverage differs".into());
        }
        receipt["status"]="completed".into();receipt["report_sha256"]=response["report_sha256"].clone();
        persist(&mut file,&receipt)?;
        if result["status"]!="passed" {return Err("isolated session suite failed; see the retained report".into());}Ok(())
    })();
    if let Err(error)=&exchange {
        if receipt["status"]!="completed" {receipt["status"]="unknown-or-error".into();}
        receipt["error"]=error.clone().into();persist(&mut file,&receipt)?;
    }
    exchange
}
