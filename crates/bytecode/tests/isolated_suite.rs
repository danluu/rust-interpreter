#![cfg(all(target_arch = "aarch64", target_os = "macos"))]
use rust_interp_bytecode::{Function, Op, Program, Slot, VERSION, HEAP_POINTER_TAG};
use serde_json::Value;
use sha2::{Digest, Sha256};
use std::{path::{Path, PathBuf}, process::{Command, Output}, sync::atomic::{AtomicUsize, Ordering}};

static NEXT: AtomicUsize = AtomicUsize::new(0);
struct Files(PathBuf);
impl Files {
    fn new() -> Self {
        let path = std::env::temp_dir().join(format!("rust-interp-suite-{}-{}", std::process::id(), NEXT.fetch_add(1, Ordering::Relaxed)));
        std::fs::create_dir(&path).unwrap(); Self(path)
    }
    fn program(&self, p: &Program) -> PathBuf {
        let path = self.0.join("program.rbc"); std::fs::write(&path, bincode::serialize(p).unwrap()).unwrap(); path
    }
}
impl Drop for Files { fn drop(&mut self) { std::fs::remove_dir_all(&self.0).unwrap(); } }

fn function(name: &str, code: Vec<Op>) -> Function {
    Function { name: name.into(), frame_size: 16, frame_align: 16, registers: 3,
        args: vec![], result: Slot { offset: 0, size: 0 }, code }
}
fn fixture(failure: bool) -> Program {
    let entry = |name: &str| function(name, vec![Op::Local { dst: 0, offset: 0 },
        Op::Call { function: 2, args: vec![], destination: 0 }, Op::Return]);
    let mut first = entry("first");
    if failure { first.code[2] = Op::Trap { message: "selected failure".into() }; }
    let shared = function("shared", vec![Op::Imm { dst: 0, value: (HEAP_POINTER_TAG + 16) as u128 },
        Op::Load { dst: 1, address: 0, size: 8 },
        Op::Assert { value: 1, expected: false, message: "previous test leaked statics".into() },
        Op::Imm { dst: 1, value: 1 }, Op::Store { address: 0, src: 1, size: 8 }, Op::Return]);
    let root = Function { name: "selected test batch: first, second".into(), frame_size: 0,
        frame_align: 16, registers: 1, args: vec![], result: Slot { offset: 0, size: 0 },
        code: vec![Op::Local { dst: 0, offset: 0 }, Op::ResetThreadLocals,
            Op::Call { function: 0, args: vec![], destination: 0 }, Op::ResetThreadLocals,
            Op::Call { function: 1, args: vec![], destination: 0 }, Op::Return] };
    Program { version: VERSION, target: "aarch64-apple-darwin".into(), entry: 3,
        functions: vec![first, entry("second"), shared, root], data: vec![0; 16],
        statics: vec![0; 32], thread_locals: vec![] }
}
fn command(program: &Path, mode: &str, report: &Path, extra: &[&str]) -> Output {
    Command::new(env!("CARGO_BIN_EXE_rust-interp-vm"))
        .args(["--engine", "jit", "--jit-resumable-calls", "--jit-persistent-registers", "--isolated-batch", mode,
               "--suite-report"]).arg(report).args(extra).arg(program).output().unwrap()
}

#[test]
fn distinct_selected_tests_share_only_prepared_code_and_report_each_outcome() {
    let files = Files::new(); let artifact = files.program(&fixture(false));
    let mut reports = vec![];
    for mode in ["fresh", "prepared"] {
        let path = files.0.join(format!("{mode}.json"));
        let run = command(&artifact, mode, &path, &[]);
        assert!(run.status.success(), "{}", String::from_utf8_lossy(&run.stderr));
        assert_eq!(run.stdout, b"0\n");
        let report: Value = serde_json::from_slice(&std::fs::read(path).unwrap()).unwrap();
        assert_eq!(report["passed"], 2); assert_eq!(report["failed"], 0);
        assert_eq!(report["tests"][0]["name"], "first"); assert_eq!(report["tests"][1]["name"], "second");
        assert_eq!(report["tests"][0]["jit_compiled_functions"], 2);
        assert_eq!(report["tests"][1]["jit_compiled_functions"], if mode == "fresh" {2} else {3});
        reports.push(report);
    }
    for index in 0..2 { for field in ["instructions", "peak_guest_memory"] {
        assert_eq!(reports[0]["tests"][index][field], reports[1]["tests"][index][field]);
    } }
    // A callee compiled by the preceding test lets a later Call enter native
    // code immediately. Backend coverage may increase; logical guest steps
    // and memory must still be identical to fresh execution.
    for index in 0..2 {
        assert!(reports[1]["tests"][index]["jit_instructions"].as_u64().unwrap()
            >= reports[0]["tests"][index]["jit_instructions"].as_u64().unwrap());
    }
}

#[test]
fn a_failed_test_is_reported_and_the_next_test_starts_clean() {
    let files = Files::new(); let artifact = files.program(&fixture(true));
    for mode in ["fresh", "prepared"] {
        let path = files.0.join(format!("{mode}.json"));
        let run = command(&artifact, mode, &path, &[]);
        assert!(!run.status.success()); assert!(run.stdout.is_empty());
        let report: Value = serde_json::from_slice(&std::fs::read(path).unwrap()).unwrap();
        assert_eq!(report["status"], "failed"); assert_eq!(report["failed"], 1); assert_eq!(report["passed"], 1);
        assert_eq!(report["tests"][0]["status"], "failed");
        assert!(report["tests"][0]["error"].as_str().unwrap().contains("selected failure"));
        assert_eq!(report["tests"][1]["status"], "passed");
    }
}

#[test]
fn malformed_batches_incompatible_flags_and_existing_reports_are_rejected() {
    let files = Files::new(); let p = fixture(false); let artifact = files.program(&p);
    let report = files.0.join("report.json");
    std::fs::write(&report, b"retained result").unwrap();
    assert!(!command(&artifact, "prepared", &report, &[]).status.success());
    assert_eq!(std::fs::read(&report).unwrap(), b"retained result");
    for (index, extra) in [vec!["--engine", "interpreter"], vec!["--jit-native-calls"],
        vec!["--profile", "unused-profile.json"], vec!["--isolated-batch", "prepared"]].into_iter().enumerate() {
        let out = files.0.join(format!("bad-options-{index}.json"));
        assert!(!command(&artifact, "prepared", &out, &extra).status.success());
        assert!(!out.exists());
    }
    for index in 0..5 {
        let mut bad = p.clone();
        match index {
            0 => bad.entry = 0,
            1 => bad.functions[3].name = "selected test batch: first, first".into(),
            2 => bad.functions[3].code[4] = Op::Call { function: 0, args: vec![], destination: 0 },
            3 => bad.functions[3].code[1] = Op::Imm { dst: 0, value: 0 },
            _ => bad.version |= rust_interp_bytecode::PARTIAL_VALIDATION,
        }
        let artifact = files.program(&bad); let out = files.0.join(format!("bad-program-{index}.json"));
        assert!(!command(&artifact, "prepared", &out, &[]).status.success()); assert!(!out.exists());
    }
}

fn catalog(program: &Program) -> rust_interp_bytecode::EntryCatalog {
    rust_interp_bytecode::EntryCatalog::new(program, format!("{:x}", Sha256::digest(bincode::serialize(program).unwrap())),
        (0..2).map(|function| rust_interp_bytecode::SelectedEntry {
            name: ["first", "second"][function].into(), function,
            body_name: program.functions[function].name.clone(),
        }).collect()).unwrap()
}

#[test]
fn explicit_catalog_survives_actual_batch_call_optimization_and_isolates_failures() {
    for failure in [false, true] {
        let files = Files::new();
        let original = fixture(failure);
        let (program, _) = rust_interp_bytecode::optimize_calls(original.clone(), Some(Default::default())).unwrap();
        assert_ne!(bincode::serialize(&program.functions[program.entry]).unwrap(),
                   bincode::serialize(&original.functions[original.entry]).unwrap());
        let artifact = files.program(&program);
        let catalog_path = files.0.join("entries.json");
        std::fs::write(&catalog_path, serde_json::to_vec(&catalog(&program)).unwrap()).unwrap();
        for mode in ["fresh", "prepared"] {
            let report = files.0.join(format!("{mode}.json"));
            let run = command(&artifact, mode, &report, &["--suite-catalog", catalog_path.to_str().unwrap()]);
            assert_eq!(run.status.success(), !failure, "{}", String::from_utf8_lossy(&run.stderr));
            let report: Value = serde_json::from_slice(&std::fs::read(report).unwrap()).unwrap();
            assert_eq!(report["entry_source"], "artifact-bound catalog");
            assert_eq!(report["passed"], if failure {1} else {2});
            assert_eq!(report["failed"], usize::from(failure));
            assert_eq!(report["tests"][0]["name"], "first");
            assert_eq!(report["tests"][1]["name"], "second");
            assert_eq!(report["tests"][1]["status"], "passed");
        }
    }
}

#[test]
fn bad_catalogs_reject_before_report_creation_or_guest_execution() {
    let files = Files::new(); let program = fixture(false); let artifact = files.program(&program);
    let valid = serde_json::to_value(catalog(&program)).unwrap();
    for index in 0..12 {
        let mut bad = valid.clone();
        match index {
            0 => bad["artifact_sha256"] = "0".repeat(64).into(),
            1 => bad["schema_version"] = 2.into(),
            2 => bad["bytecode_version"] = (VERSION | rust_interp_bytecode::PARTIAL_VALIDATION).into(),
            3 => bad["target"] = "other-target".into(),
            4 => bad["program_entry"] = 0.into(),
            5 => bad["entries"][1]["function"] = 0.into(),
            6 => bad["entries"][0]["function"] = 999.into(),
            7 => bad["entries"][1]["name"] = "first".into(),
            8 => bad["entries"][0]["body_name"] = "wrong-body".into(),
            9 => bad["entries"].as_array_mut().unwrap().clear(),
            10 => bad["unrecognized"] = true.into(),
            _ => {
                // Change same-sized bytecode, preserving names, signatures and
                // entry IDs. The previous catalog must still be rejected.
                let mut changed = program.clone(); changed.data[0] ^= 1; files.program(&changed);
            }
        }
        let path = files.0.join(format!("catalog-{index}.json"));
        std::fs::write(&path, serde_json::to_vec(&bad).unwrap()).unwrap();
        let report = files.0.join(format!("rejected-{index}.json"));
        let run = command(&artifact, "prepared", &report, &["--suite-catalog", path.to_str().unwrap()]);
        assert!(!run.status.success(), "accepted malformed catalog {index}");
        assert!(!report.exists());
    }
    for mutate in 0..3 {
        let mut invalid = program.clone();
        match mutate {
            0 => invalid.functions[0].args.push(Slot {offset: 0, size: 8}),
            1 => invalid.functions[0].result.size = 8,
            _ => invalid.version |= rust_interp_bytecode::PARTIAL_VALIDATION,
        }
        assert!(serde_json::from_value::<rust_interp_bytecode::EntryCatalog>(valid.clone()).unwrap()
            .validated_entries(&invalid, &bincode::serialize(&invalid).unwrap()).is_err());
    }
}
