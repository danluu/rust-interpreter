//! Private local endpoint around the qualified session request path.
use super::*;
use std::os::{fd::AsRawFd,unix::{fs::{DirBuilderExt,MetadataExt,OpenOptionsExt,PermissionsExt},net::UnixListener}};

// Darwin SDK sys/poll.h: nfds_t is unsigned int; pollfd is int/short/short.
#[repr(C)]
struct PollFd {fd:std::ffi::c_int,events:std::ffi::c_short,revents:std::ffi::c_short}
unsafe extern "C" {fn poll(fds:*mut PollFd,count:std::ffi::c_uint,timeout:std::ffi::c_int)->std::ffi::c_int;}
fn await_connection(listener:&UnixListener)->Result<bool,String> {
    const INPUT:i16=0x0001;const ERROR:i16=0x0008;const HANGUP:i16=0x0010;const INVALID:i16=0x0020;
    loop {
        let mut fds=[PollFd{fd:0,events:INPUT,revents:0},PollFd{fd:listener.as_raw_fd(),events:INPUT,revents:0}];
        // Both descriptors remain owned/open for the duration of the call.
        if unsafe {poll(fds.as_mut_ptr(),fds.len() as u32,-1)}<0 {
            let error=std::io::Error::last_os_error();
            if error.kind()==std::io::ErrorKind::Interrupted {continue;}
            return Err(error.to_string());
        }
        if fds.iter().any(|fd|fd.revents&(ERROR|INVALID)!=0) {return Err("session descriptor polling failed".into());}
        if fds[0].revents&(INPUT|HANGUP)!=0 {
            let mut byte=[0];
            match std::io::stdin().read(&mut byte) {
                Ok(0)=>return Ok(false),
                Ok(_)=>return Err("socket session owner pipe accepts only EOF".into()),
                Err(error) if error.kind()==std::io::ErrorKind::Interrupted=>continue,
                Err(error)=>return Err(error.to_string()),
            }
        }
        if fds[1].revents&HANGUP!=0 {return Err("session listener closed".into());}
        if fds[1].revents&INPUT!=0 {return Ok(true);}
    }
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Authenticated {auth:String,executable_sha256:String,request:Request}

fn token_equal(a:&str,b:&str)->bool {
    a.len()==64 && b.len()==64 && a.bytes().zip(b.bytes()).fold(0u8,|difference,(a,b)|difference|(a^b))==0
}
fn reject(stream:&mut impl Write,error:&str)->Result<(),String> {
    write_frame(stream,&json!({"kind":"rejected","error":error,"execution_possible":false}))
}
pub(super) fn serve(directory:&str,bytes:usize,verify:bool)->Result<(),String> {
    let startup=cpu()?;
    let directory=absolute(directory)?;
    let parent=directory.parent().ok_or("missing session directory parent")?;
    if parent.canonicalize().map_err(|e|e.to_string())?!=parent || directory.file_name().is_none() {
        return Err("session directory must have a canonical existing parent".into());
    }
    // create_dir is exclusive: never attach to, replace or clean an old endpoint.
    std::fs::DirBuilder::new().mode(0o700).create(directory).map_err(|e|e.to_string())?;
    let metadata=directory.symlink_metadata().map_err(|e|e.to_string())?;
    if !metadata.is_dir() || metadata.mode()&0o777!=0o700 {return Err("session directory is not private".into());}
    let path=directory.join("socket");let listener=UnixListener::bind(&path).map_err(|e|e.to_string())?;
    std::fs::set_permissions(&path,std::fs::Permissions::from_mode(0o600)).map_err(|e|e.to_string())?;
    let mut entropy=[0u8;32];std::fs::File::open("/dev/urandom").and_then(|mut f|f.read_exact(&mut entropy)).map_err(|e|e.to_string())?;
    let auth=entropy.iter().map(|b|format!("{b:02x}")).collect::<String>();
    let mut pool=Pool::new(bytes,verify)?;let mut ready=readiness(bytes,verify,startup)?;
    ready["socket"]=path.to_string_lossy().as_ref().into();ready["ready_path"]=directory.join("ready.json").to_string_lossy().as_ref().into();
    ready["cwd"]=std::env::current_dir().map_err(|e|e.to_string())?.to_string_lossy().as_ref().into();
    let mut private=ready.clone();private["auth"]=auth.clone().into();
    let mut file=std::fs::OpenOptions::new().write(true).create_new(true).mode(0o600).open(directory.join("ready.json")).map_err(|e|e.to_string())?;
    file.write_all(&serde_json::to_vec(&private).map_err(|e|e.to_string())?).and_then(|_|file.sync_data()).map_err(|e|e.to_string())?;
    // The bearer token exists only in the private file and inbound frames.
    // stdout, reports and responses contain the public identity alone.
    write_frame(&mut std::io::stdout().lock(),&ready)?;
    let mut expected=1u64;let mut connections=0usize;
    while await_connection(&listener)? {
        let (mut stream,_)=listener.accept().map_err(|e|e.to_string())?;connections+=1;
        if connections>8192 {return Err("session connection limit exceeded".into());}
        stream.set_read_timeout(Some(std::time::Duration::from_secs(30))).map_err(|e|e.to_string())?;
        stream.set_write_timeout(Some(std::time::Duration::from_secs(30))).map_err(|e|e.to_string())?;
        let before=cpu()?;
        let greeting=json!({"kind":"greeting","schema":1,"next_id":expected,"pid":std::process::id(),
            "executable_sha256":ready["executable_sha256"]});
        if write_frame(&mut stream,&greeting).is_err() {continue;}
        let input=match read_frame(&mut stream) {
            Ok(Some(input))=>input,Ok(None)=>continue,
            Err(_)=>{let _=reject(&mut stream,"invalid or incomplete session frame");continue;},
        };
        let authenticated:Authenticated=match serde_json::from_slice(&input) {
            Ok(value)=>value,Err(_)=>{let _=reject(&mut stream,"invalid session request shape");continue;},
        };
        if !token_equal(&authenticated.auth,&auth) || authenticated.executable_sha256!=ready["executable_sha256"].as_str().unwrap() {
            let _=reject(&mut stream,"session authentication or executable identity differs");continue;
        }
        let request=authenticated.request;
        if request.schema!=1 || request.id!=expected || expected>4096 {
            let _=reject(&mut stream,"session request schema, sequence or count differs");continue;
        }
        expected+=1;
        if matches!(request.body,Body::Shutdown{}) {
            drop(pool);
            let closed=json!({"kind":"closed","id":request.id,"requests_consumed":expected-1,
                "cpu_at_close":cpu()?,"pid":std::process::id(),"executable_sha256":ready["executable_sha256"]});
            // A lost response never repeats the shutdown or any guest request.
            let _=write_frame(&mut stream,&closed);
            write_frame(&mut std::io::stdout().lock(),&closed)?;return Ok(());
        }
        let started=Instant::now();let mut response=match run_request(&mut pool,request.id,request.body) {
            Ok(result)=>result,
            Err(error)=>json!({"kind":"error","id":request.id,"error":error.chars().take(4096).collect::<String>(),
                "execution_possible":true,"poisoned":pool.poisoned}),
        };
        response["cpu_before"]=serde_json::to_value(before).unwrap();response["cpu_after"]=serde_json::to_value(cpu()?).unwrap();
        response["request_seconds"]=started.elapsed().as_secs_f64().into();
        response["pid"]=std::process::id().into();response["executable_sha256"]=ready["executable_sha256"].clone();
        let poisoned=response["poisoned"]==true;
        // The report was reserved before execution and its result is retained.
        // A disconnected client gets no automatic replay on the next connection.
        let _=write_frame(&mut stream,&response);
        if poisoned {return Err("session worker failed; session closed".into());}
    }
    drop(pool);
    write_frame(&mut std::io::stdout().lock(),&json!({"kind":"closed","reason":"owner_eof",
        "requests_consumed":expected-1,"cpu_at_close":cpu()?,"pid":std::process::id(),
        "executable_sha256":ready["executable_sha256"]}))
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn authentication_requires_the_complete_instance_token() {
        let token="a".repeat(64);assert!(token_equal(&token,&token));
        assert!(!token_equal(&token,&"a".repeat(63)));assert!(!token_equal(&token,&"b".repeat(64)));
        assert!(serde_json::from_value::<Authenticated>(json!({"auth":token,"executable_sha256":"id",
            "request":{"schema":1,"id":1,"body":{"command":"shutdown"}},"extra":true})).is_err());
    }
}
