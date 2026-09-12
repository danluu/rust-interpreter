use rust_interp_bytecode::{Function,Op,Program,Slot,VERSION};
use std::path::PathBuf;
use std::process::Command;
struct Directory(PathBuf);
impl Directory {
    fn new()->Self {let p=std::env::temp_dir().join(format!("rust-interp-call-census-{}-{}",std::process::id(),std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_nanos()));std::fs::create_dir(&p).unwrap();Self(p)}
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

#[test]
fn fold_command_and_whole_artifact_verifier_match_a_separate_expected_program() {
    let d=Directory::new();let input=d.0.join("input.rbc");let output=d.0.join("folded.rbc");let report=d.0.join("fold.json");
    let mut p=program();p.functions[0].registers=1;p.functions[0].code.insert(0,Op::Imm{dst:0,value:123});
    std::fs::write(&input,bincode::serialize(&p).unwrap()).unwrap();
    assert!(Command::new(env!("CARGO_BIN_EXE_rust-interp-call-census")).args(["--fold"]).arg(&input).arg(&output).arg(&report).output().unwrap().status.success());
    p.functions[0].code.remove(0);let expected=bincode::serialize(&p).unwrap();assert_eq!(std::fs::read(&output).unwrap(),expected);
    let checked=d.0.join("checked.json");
    assert!(Command::new(env!("CARGO_BIN_EXE_rust-interp-call-census")).arg("--verify-fold").arg(&input).arg(&output).arg(&checked).output().unwrap().status.success());
    let r:serde_json::Value=serde_json::from_slice(&std::fs::read(&checked).unwrap()).unwrap();assert_eq!(r["exact_constant_fold"],true);
    let before=std::fs::read(&report).unwrap();
    assert!(!Command::new(env!("CARGO_BIN_EXE_rust-interp-call-census")).arg("--fold").arg(&input).arg(&output).arg(&report).output().unwrap().status.success());
    assert_eq!(std::fs::read(&output).unwrap(),expected);assert_eq!(std::fs::read(&report).unwrap(),before);
}
#[test]
fn fold_verifier_rejects_unrelated_data_and_layout_changes() {
    let d=Directory::new();let input=d.0.join("input.rbc");let candidate=d.0.join("candidate.rbc");let p=program();
    std::fs::write(&input,bincode::serialize(&p).unwrap()).unwrap();
    for index in 0..2 {
        let mut other=p.clone();if index==0 {other.data.push(1);} else {other.functions[0].frame_size=1;}
        std::fs::write(&candidate,bincode::serialize(&other).unwrap()).unwrap();let report=d.0.join(format!("{index}.json"));
        assert!(!Command::new(env!("CARGO_BIN_EXE_rust-interp-call-census")).arg("--verify-fold").arg(&input).arg(&candidate).arg(&report).output().unwrap().status.success());
        let r:serde_json::Value=serde_json::from_slice(&std::fs::read(report).unwrap()).unwrap();assert_eq!(r["exact_constant_fold"],false);
    }
}
