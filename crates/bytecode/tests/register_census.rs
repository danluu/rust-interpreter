use rust_interp_bytecode::{Function, Op, Program, Slot, VERSION};
use std::{path::PathBuf, process::Command};

struct Files(PathBuf);
impl Drop for Files { fn drop(&mut self) { std::fs::remove_dir_all(&self.0).unwrap(); } }

#[test]
fn census_is_offline_validates_input_and_preserves_existing_reports() {
    let files = Files(std::env::temp_dir().join(format!("rust-interp-register-census-{}", std::process::id())));
    std::fs::create_dir(&files.0).unwrap();
    let mut program = Program { version:VERSION,target:"aarch64-apple-darwin".into(),entry:0,
        data:vec![0;16],statics:vec![],thread_locals:vec![],functions:vec![Function {
            name:"trap_if_executed".into(),frame_size:0,frame_align:16,registers:1,args:vec![],
            result:Slot {offset:0,size:0},code:vec![Op::Imm {dst:0,value:42},
                Op::Trap {message:"census must not execute this body".into()}]}] };
    let artifact = files.0.join("program.rbc");
    std::fs::write(&artifact,bincode::serialize(&program).unwrap()).unwrap();
    let report = files.0.join("report.json");
    let run = |out: &std::path::Path| Command::new(env!("CARGO_BIN_EXE_rust-interp-register-census"))
        .arg(&artifact).arg(out).output().unwrap();
    let result = run(&report);
    assert!(result.status.success(),"{}",String::from_utf8_lossy(&result.stderr));
    let original = std::fs::read(&report).unwrap();
    let parsed: serde_json::Value = serde_json::from_slice(&original).unwrap();
    assert_eq!(parsed["kind"],"register-width-census");
    assert_eq!(parsed["functions"][0]["proven_narrow"],1);
    assert!(!run(&report).status.success());
    assert_eq!(std::fs::read(&report).unwrap(),original);
    let profile = files.0.join("profile.json");
    let f = &program.functions[0];
    std::fs::write(&profile, serde_json::to_vec(&serde_json::json!({"functions":[{
        "name":f.name,"frame_size":f.frame_size,"registers":f.registers,
        "operations":f.code.iter().map(|op|format!("{op:?}")).collect::<Vec<_>>(),
        "interpreted":[0,0],"jit_blocks":[7,0],"jit_block_ends":[2,0],
        "jit_tree_blocks":[0,0],"jit_tree_block_ends":[0,0]
    }]})).unwrap()).unwrap();
    let weighted = files.0.join("weighted.json");
    let result = Command::new(env!("CARGO_BIN_EXE_rust-interp-register-census"))
        .arg(&artifact).arg(&weighted).arg(&profile).output().unwrap();
    assert!(result.status.success(),"{}",String::from_utf8_lossy(&result.stderr));
    let parsed: serde_json::Value = serde_json::from_slice(&std::fs::read(weighted).unwrap()).unwrap();
    assert_eq!(parsed["functions"][0]["native_operation_executions"],14);
    assert_eq!(parsed["functions"][0]["native_read_operands"],0);
    assert_eq!(parsed["profile_sha256"].as_str().unwrap().len(),64);
    program.functions[0].code[0] = Op::Imm {dst:99,value:42};
    std::fs::write(&artifact,bincode::serialize(&program).unwrap()).unwrap();
    let invalid = files.0.join("invalid.json");
    assert!(!run(&invalid).status.success());assert!(!invalid.exists());
}
