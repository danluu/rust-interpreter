use rust_interp_bytecode::{Function,Op,Program,Slot,VERSION};
use std::{path::PathBuf,process::Command};

fn setup(label:&str)->(PathBuf,Program,Program) {
    let directory=std::env::temp_dir().join(format!("rust-interp-lifetime-verifier-{}-{label}",std::process::id()));
    std::fs::create_dir(&directory).unwrap();
    let original=Program {version:VERSION,target:"aarch64-apple-darwin".into(),entry:0,data:vec![0;16],statics:vec![],thread_locals:vec![],
        functions:vec![Function {name:"verify".into(),frame_size:8,frame_align:8,registers:6,args:vec![],result:Slot{offset:0,size:8},
            code:vec![Op::Local{dst:0,offset:0},Op::Imm{dst:4,value:7},Op::Store{address:0,src:4,size:8},
                Op::Imm{dst:5,value:9},Op::Store{address:0,src:5,size:8},Op::Return]}]};
    let mut expected=original.clone();expected.functions[0].registers=2;
    expected.functions[0].code=vec![Op::Local{dst:0,offset:0},Op::Imm{dst:1,value:7},Op::Store{address:0,src:1,size:8},
        Op::Imm{dst:1,value:9},Op::Store{address:0,src:1,size:8},Op::Return];
    (directory,original,expected)
}

#[test]
fn exact_verifier_accepts_hand_written_allocation_and_preserves_existing_reports() {
    let (directory,original,expected)=setup("accept");
    for (name,p) in [("a",original),("b",expected)] {std::fs::write(directory.join(name),bincode::serialize(&p).unwrap()).unwrap();}
    let call=||Command::new(env!("CARGO_BIN_EXE_rust-interp-lifetime-census")).arg("--verify")
        .arg(directory.join("a")).arg(directory.join("b")).arg(directory.join("report.json")).output().unwrap();
    let output=call();assert!(output.status.success(),"{}",String::from_utf8_lossy(&output.stderr));
    let bytes=std::fs::read(directory.join("report.json")).unwrap();
    assert_eq!(serde_json::from_slice::<serde_json::Value>(&bytes).unwrap()["exact_allocation"],true);
    assert!(!call().status.success());assert_eq!(std::fs::read(directory.join("report.json")).unwrap(),bytes);
    std::fs::remove_dir_all(directory).unwrap();
}

#[test]
fn exact_verifier_rejects_unrelated_layout_and_constant_changes() {
    let (directory,original,expected)=setup("reject");
    std::fs::write(directory.join("a"),bincode::serialize(&original).unwrap()).unwrap();
    for index in 0..2 {
        let mut changed=expected.clone();
        if index==0 {changed.functions[0].frame_size=16;} else {changed.functions[0].code[1]=Op::Imm{dst:1,value:8};}
        std::fs::write(directory.join("b"),bincode::serialize(&changed).unwrap()).unwrap();
        let report=directory.join(format!("report-{index}.json"));
        let output=Command::new(env!("CARGO_BIN_EXE_rust-interp-lifetime-census")).arg("--verify")
            .arg(directory.join("a")).arg(directory.join("b")).arg(&report).output().unwrap();
        assert!(!output.status.success());
        assert_eq!(serde_json::from_slice::<serde_json::Value>(&std::fs::read(report).unwrap()).unwrap()["exact_allocation"],false);
    }
    std::fs::remove_dir_all(directory).unwrap();
}
