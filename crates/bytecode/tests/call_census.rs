use rust_interp_bytecode::{Function,Op,Program,Slot,VERSION};
use std::path::PathBuf;
use std::process::Command;
static DIRECTORY_ID: std::sync::atomic::AtomicU64 = std::sync::atomic::AtomicU64::new(0);
struct Directory(PathBuf);
impl Directory {
    fn new()->Self {let p=std::env::temp_dir().join(format!("rust-interp-call-census-{}-{}-{}",std::process::id(),std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_nanos(),DIRECTORY_ID.fetch_add(1,std::sync::atomic::Ordering::Relaxed)));std::fs::create_dir(&p).unwrap();Self(p)}
}
impl Drop for Directory {fn drop(&mut self){std::fs::remove_dir_all(&self.0).unwrap();}}
fn program()->Program {Program {version:VERSION,target:"aarch64-apple-darwin".into(),entry:0,data:vec![],statics:vec![],thread_locals:vec![],functions:vec![Function{name:"test".into(),frame_size:0,frame_align:16,registers:0,args:vec![],result:Slot{offset:0,size:0},code:vec![Op::Return]}]}}
#[test]
fn diagnostic_writes_bound_digest_and_preserves_existing_output() {
    let d=Directory::new();let input=d.0.join("input.rbc");let output=d.0.join("output.json");
    std::fs::write(&input,bincode::serialize(&program()).unwrap()).unwrap();
    let run=||Command::new(env!("CARGO_BIN_EXE_rust-interp-call-census")).arg(&input).arg(&output).output().unwrap();
    assert!(run().status.success());let before=std::fs::read(&output).unwrap();let report:serde_json::Value=serde_json::from_slice(&before).unwrap();
    assert_eq!(report["direct_call_sites"],0);assert_eq!(report["artifact_sha256"].as_str().unwrap().len(),64);
    assert!(!run().status.success());assert_eq!(std::fs::read(&output).unwrap(),before);
}
#[test]
fn diagnostic_rejects_nonregular_large_invalid_and_trailing_inputs() {
    let d=Directory::new();let input=d.0.join("input.rbc");let output=d.0.join("output.json");
    let run=|p:&std::path::Path|Command::new(env!("CARGO_BIN_EXE_rust-interp-call-census")).arg(p).arg(&output).output().unwrap();
    assert!(!run(&d.0).status.success());
    std::fs::File::create(&input).unwrap().set_len(64*1024*1024+1).unwrap();assert!(!run(&input).status.success());
    std::fs::write(&input,b"invalid").unwrap();assert!(!run(&input).status.success());
    let mut bytes=bincode::serialize(&program()).unwrap();bytes.push(0);std::fs::write(&input,bytes).unwrap();assert!(!run(&input).status.success());assert!(!output.exists());
}
