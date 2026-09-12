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

fn many_entries(failure: bool) -> Program {
    let original = fixture(failure);
    let mut p = original.clone();
    let count = 8;
    let mut functions = vec![];
    let names: Vec<_> = (0..count).map(|index| format!("case-{index:02}")).collect();
    for (index, name) in names.iter().enumerate() {
        let mut entry = original.functions[usize::from(index != 0)].clone();
        entry.name = name.clone();
        entry.code[1] = Op::Call { function: count, args: vec![], destination: 0 };
        functions.push(entry);
    }
    functions.push(original.functions[2].clone());
    let mut root = original.functions[3].clone();
    root.name = format!("selected test batch: {}", names.join(", "));
    root.code = vec![Op::Local { dst: 0, offset: 0 }];
    for function in 0..count {
        root.code.extend([Op::ResetThreadLocals, Op::Call { function, args: vec![], destination: 0 }]);
    }
    root.code.push(Op::Return);
    functions.push(root);
    p.functions = functions; p.entry = count + 1; p
}

#[test]
fn parallel_workers_preserve_test_state_and_catalog_order() {
    let files = Files::new(); let program = many_entries(false); let artifact = files.program(&program);
    let catalog = rust_interp_bytecode::EntryCatalog::new(&program,
        format!("{:x}", Sha256::digest(std::fs::read(&artifact).unwrap())),
        (0..8).map(|function| rust_interp_bytecode::SelectedEntry {
            name: program.functions[function].name.clone(), function,
            body_name: program.functions[function].name.clone(),
        }).collect()).unwrap();
    let catalog_path = files.0.join("entries.json");
    let catalog_bytes = serde_json::to_vec(&catalog).unwrap();
    std::fs::write(&catalog_path, &catalog_bytes).unwrap();
    let mut expected = None;
    for mode in ["fresh", "prepared"] {
        for workers in [1, 2, 3, 64] {
            let path = files.0.join(format!("{mode}-{workers}.json"));
            let workers_text = workers.to_string();
            let mut extra = vec!["--suite-workers", &workers_text];
            if workers == 2 || workers == 64 { extra.extend(["--suite-catalog", catalog_path.to_str().unwrap()]); }
            let run = command(&artifact, mode, &path, &extra);
            assert!(run.status.success(), "{}", String::from_utf8_lossy(&run.stderr));
            let report: Value = serde_json::from_slice(&std::fs::read(path).unwrap()).unwrap();
            assert_eq!(report["workers"], workers.min(8));
            assert_eq!(report["requested_workers"], workers);
            assert_eq!(report["passed"], 8); assert_eq!(report["failed"], 0);
            let mut outcomes = vec![];
            for (index, test) in report["tests"].as_array().unwrap().iter().enumerate() {
                assert_eq!(test["name"], format!("case-{index:02}"));
                assert_eq!(test["function"], index);
                assert!(test["worker"].as_u64().unwrap() < workers.min(8));
                assert!(test["jit_bytes"].as_u64().unwrap() <= 16 * 1024 * 1024);
                outcomes.push((test["instructions"].clone(), test["peak_guest_memory"].clone()));
            }
            if let Some(expected) = &expected { assert_eq!(&outcomes, expected); }
            else { expected = Some(outcomes); }
        }
    }
    assert_eq!(std::fs::read(catalog_path).unwrap(), catalog_bytes);
}

#[test]
fn parallel_failures_and_limits_do_not_skip_other_tests() {
    let files = Files::new(); let artifact = files.program(&many_entries(true));
    for mode in ["fresh", "prepared"] {
        for limited in [false, true] {
            let path = files.0.join(format!("{mode}-{limited}.json"));
            let mut extra = vec!["--suite-workers", "3"];
            if limited { extra.extend(["--instruction-limit", "1"]); }
            let run = command(&artifact, mode, &path, &extra);
            assert!(!run.status.success());
            let report: Value = serde_json::from_slice(&std::fs::read(path).unwrap()).unwrap();
            assert_eq!(report["tests"].as_array().unwrap().len(), 8);
            assert_eq!(report["failed"], if limited { 8 } else { 1 });
            for (index, test) in report["tests"].as_array().unwrap().iter().enumerate() {
                assert_eq!(test["name"], format!("case-{index:02}"));
                if limited { assert!(test["error"].as_str().unwrap().contains("instruction limit")); }
                else if index == 0 { assert!(test["error"].as_str().unwrap().contains("selected failure")); }
                else { assert_eq!(test["status"], "passed"); }
            }
        }
    }
}

#[test]
fn invalid_worker_requests_preserve_reports_and_require_isolation() {
    let files = Files::new(); let artifact = files.program(&fixture(false));
    for (index, extra) in [vec!["--suite-workers", "0"], vec!["--suite-workers", "65"],
        vec!["--suite-workers", "-1"], vec!["--suite-workers", "2", "--suite-workers", "3"],
        vec!["--suite-workers", "2", "--profile", "unused-profile.json"]].iter().enumerate() {
        let path = files.0.join(format!("invalid-workers-{index}.json"));
        assert!(!command(&artifact, "prepared", &path, extra).status.success());
        assert!(!path.exists());
    }
    let path = files.0.join("retained.json"); std::fs::write(&path, b"retained").unwrap();
    assert!(!command(&artifact, "prepared", &path, &["--suite-workers", "2"]).status.success());
    assert_eq!(std::fs::read(path).unwrap(), b"retained");
    let run = Command::new(env!("CARGO_BIN_EXE_rust-interp-vm"))
        .args(["--suite-workers", "1"]).arg(&artifact).output().unwrap();
    assert!(!run.status.success());
    assert!(String::from_utf8_lossy(&run.stderr).contains("require an isolated batch"));
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
        assert_eq!(report["runtime_limits"]["allocations"], 100_000);
        assert_eq!(report["runtime_limits"]["instructions"], 100_000_000);
        assert_eq!(report["runtime_limits"]["memory_bytes"], 64 * 1024 * 1024);
        assert_eq!(report["runtime_limits"]["frames"], 4096);
        assert_eq!(report["jit_code_limit_bytes"], 16 * 1024 * 1024);
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
fn effective_limits_are_reported_when_each_isolated_test_exhausts_its_budget() {
    let files = Files::new(); let artifact = files.program(&fixture(false));
    for mode in ["fresh", "prepared"] {
        let path = files.0.join(format!("{mode}-limits.json"));
        let run = command(&artifact, mode, &path, &["--instruction-limit", "1", "--allocation-limit", "150000"]);
        assert!(!run.status.success());
        let report: Value = serde_json::from_slice(&std::fs::read(path).unwrap()).unwrap();
        assert_eq!(report["runtime_limits"]["allocations"], 150_000);
        assert_eq!(report["runtime_limits"]["instructions"], 1);
        assert_eq!(report["failed"], 2);
        for test in report["tests"].as_array().unwrap() {
            assert!(test["error"].as_str().unwrap().contains("instruction limit exceeded"));
        }
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

fn profile_command(artifact: &Path, catalog: &Path, output: &Path, engine: &str, name: &str) -> Command {
    let mut command=Command::new(env!("CARGO_BIN_EXE_rust-interp-vm"));
    command.args(["--engine",engine]);
    if engine=="jit" {command.args(["--jit-resumable-calls","--jit-persistent-registers"]);}
    command.args(["--profile-test",name,"--suite-catalog"]).arg(catalog).arg("--profile").arg(output).arg(artifact);
    command
}

#[test]
fn catalog_profile_runs_only_the_exact_test_and_preserves_original_artifact() {
    let files=Files::new();let mut program=fixture(true);
    program.functions[program.entry].code=vec![Op::Trap{message:"batch root must not run".into()}];
    let artifact=files.program(&program);let before=std::fs::read(&artifact).unwrap();
    let cat=files.0.join("catalog.json");let cat_bytes=serde_json::to_vec(&catalog(&program)).unwrap();
    std::fs::write(&cat,&cat_bytes).unwrap();
    let mut all_counts=vec![];
    for engine in ["interpreter","jit"] {
        let output=files.0.join(format!("{engine}.json"));
        let run=profile_command(&artifact,&cat,&output,engine,"second").output().unwrap();
        assert!(run.status.success(),"{}",String::from_utf8_lossy(&run.stderr));assert_eq!(run.stdout,b"0\n");
        let selection:Vec<_>=String::from_utf8(run.stderr).unwrap().lines()
            .filter_map(|line|line.strip_prefix("rust-interp-profile-selection: ").map(|s|serde_json::from_str::<Value>(s).unwrap())).collect();
        assert_eq!(selection.len(),1);let selected=&selection[0];
        assert_eq!(selected["name"],"second");assert_eq!(selected["function"],1);assert_eq!(selected["original_entry"],3);
        assert_eq!(selected["artifact_sha256"],format!("{:x}",Sha256::digest(&before)));
        assert_eq!(selected["catalog_sha256"],format!("{:x}",Sha256::digest(&cat_bytes)));
        let profile:Value=serde_json::from_slice(&std::fs::read(output).unwrap()).unwrap();
        let logical:Vec<Vec<u64>>=profile["functions"].as_array().unwrap().iter().map(|f| {
            let mut counts:Vec<u64>=f["interpreted"].as_array().unwrap().iter().map(|n|n.as_u64().unwrap()).collect();
            for (pc,hits) in f["jit_blocks"].as_array().unwrap().iter().enumerate() {
                let hits=hits.as_u64().unwrap();
                if hits!=0 {for n in &mut counts[pc..f["jit_block_ends"][pc].as_u64().unwrap() as usize] {*n+=hits;}}
            }
            counts
        }).collect();
        assert_eq!(logical.len(),4);assert!(logical[0].iter().all(|&n|n==0));assert!(logical[3].iter().all(|&n|n==0));
        assert!(logical[1].iter().any(|&n|n!=0));assert!(logical[2].iter().any(|&n|n!=0));
        all_counts.push(logical);assert_eq!(std::fs::read(&artifact).unwrap(),before);
    }
    assert_eq!(all_counts[0],all_counts[1]);
}

#[test]
fn catalog_profile_rejects_unknown_stale_invalid_and_conflicting_selections_before_output() {
    let files=Files::new();let program=fixture(true);let artifact=files.program(&program);
    let original=serde_json::to_value(catalog(&program)).unwrap();let cat=files.0.join("catalog.json");
    for index in 0..6 {
        let mut contents=original.clone();
        match index {
            0=>{}, // unknown name
            1=>contents["artifact_sha256"]="0".repeat(64).into(),
            2=>contents["entries"][1]["function"]=0.into(),
            3=>contents["entries"][1]["body_name"]="wrong".into(),
            4=>contents["program_entry"]=0.into(),
            _=>{}, // valid name but entry arguments forbidden
        }
        std::fs::write(&cat,serde_json::to_vec(&contents).unwrap()).unwrap();
        let output=files.0.join(format!("rejected-{index}.json"));
        let mut cmd=profile_command(&artifact,&cat,&output,"jit",if index==0 {"absent"} else {"second"});
        if index==5 {cmd.arg("1");}
        assert!(!cmd.output().unwrap().status.success());assert!(!output.exists());
    }
    std::fs::write(&cat,serde_json::to_vec(&original).unwrap()).unwrap();
    let output=files.0.join("conflict.json");
    for extra in [vec!["--profile-test","second"],vec!["--profile-test","second","--profile-test","second"],
        vec!["--profile-test","second","--profile",output.to_str().unwrap(),"--isolated-batch","prepared","--suite-report",output.to_str().unwrap()]] {
        let run=Command::new(env!("CARGO_BIN_EXE_rust-interp-vm"))
            .args(extra).arg("--suite-catalog").arg(&cat).arg(&artifact).output().unwrap();
        assert!(!run.status.success());assert!(!output.exists());
    }
    let run=Command::new(env!("CARGO_BIN_EXE_rust-interp-vm"))
        .args(["--profile-test","second","--profile"]).arg(&output).arg(&artifact).output().unwrap();
    assert!(!run.status.success());assert!(!output.exists());
}

#[test]
fn catalog_profile_preserves_existing_output_and_reports_selected_failure() {
    let files=Files::new();let program=fixture(true);let artifact=files.program(&program);
    let cat=files.0.join("catalog.json");std::fs::write(&cat,serde_json::to_vec(&catalog(&program)).unwrap()).unwrap();
    let output=files.0.join("existing.json");std::fs::write(&output,b"preserve me").unwrap();
    assert!(!profile_command(&artifact,&cat,&output,"jit","second").output().unwrap().status.success());
    assert_eq!(std::fs::read(&output).unwrap(),b"preserve me");
    let output=files.0.join("failed.json");
    let run=profile_command(&artifact,&cat,&output,"jit","first").output().unwrap();
    assert!(!run.status.success());assert!(String::from_utf8_lossy(&run.stderr).contains("selected failure"));
    // execute_profiled returns no complete profile after a guest failure.
    assert_eq!(std::fs::metadata(output).unwrap().len(),0);
}

#[test]
fn catalog_selection_runs_without_instrumentation_and_dumps_the_selected_code() {
    let files=Files::new();let mut program=fixture(true);
    program.functions[program.entry].code=vec![Op::Trap{message:"batch root must not run".into()}];
    let artifact=files.program(&program);let before=std::fs::read(&artifact).unwrap();
    let cat=files.0.join("catalog.json");let cat_bytes=serde_json::to_vec(&catalog(&program)).unwrap();std::fs::write(&cat,&cat_bytes).unwrap();
    for engine in ["interpreter","jit"] {
        let dump=files.0.join("code");
        let mut cmd=Command::new(env!("CARGO_BIN_EXE_rust-interp-vm"));cmd.args(["--engine",engine,"--select-test","second","--suite-catalog"]).arg(&cat);
        if engine=="jit" {cmd.args(["--jit-resumable-calls","--jit-persistent-registers","--jit-code-dump"]).arg(&dump);}
        let run=cmd.arg(&artifact).output().unwrap();assert!(run.status.success(),"{}",String::from_utf8_lossy(&run.stderr));assert_eq!(run.stdout,b"0\n");
        let stderr=String::from_utf8(run.stderr).unwrap();
        let selected:Vec<Value>=stderr.lines().filter_map(|line|line.strip_prefix("rust-interp-test-selection: ").map(|s|serde_json::from_str(s).unwrap())).collect();
        assert_eq!(selected.len(),1);let selected=&selected[0];assert_eq!(selected["name"],"second");assert_eq!(selected["function"],1);
        assert_eq!(selected["artifact_sha256"],format!("{:x}",Sha256::digest(&before)));
        assert_eq!(selected["catalog_sha256"],format!("{:x}",Sha256::digest(&cat_bytes)));
        if engine=="jit" {
            let map:Value=serde_json::from_slice(&std::fs::read(dump.join("map.json")).unwrap()).unwrap();assert_eq!(map["profiled"],false);
            assert!(map["ranges"].as_array().unwrap().iter().any(|r|r["function"]==1));
            assert!(map["ranges"].as_array().unwrap().iter().all(|r|r["function"]!=0&&r["function"]!=3));
        }
        assert_eq!(std::fs::read(&artifact).unwrap(),before);
    }
}

#[test]
fn uninstrumented_selection_rejects_bad_catalogs_conflicts_and_selected_failures() {
    let files=Files::new();let program=fixture(true);let artifact=files.program(&program);
    let cat=files.0.join("catalog.json");let original=serde_json::to_value(catalog(&program)).unwrap();
    for index in 0..7 {
        let mut contents=original.clone();if index==1 {contents["artifact_sha256"]="0".repeat(64).into();}
        if index==2 {contents["entries"][1]["function"]=0.into();}
        std::fs::write(&cat,serde_json::to_vec(&contents).unwrap()).unwrap();
        let dump=files.0.join(format!("rejected-{index}"));let mut cmd=Command::new(env!("CARGO_BIN_EXE_rust-interp-vm"));
        cmd.args(["--engine","jit","--jit-resumable-calls","--select-test",if index==0 {"absent"} else {"second"}]);
        if index!=3 {cmd.arg("--suite-catalog").arg(&cat);}
        if index==4 {cmd.args(["--profile-test","second"]);}
        if index==5 {cmd.args(["--isolated-batch","prepared","--suite-report"]).arg(files.0.join("not-created.json"));}
        cmd.arg("--jit-code-dump").arg(&dump).arg(&artifact);if index==6 {cmd.arg("1");}
        assert!(!cmd.output().unwrap().status.success());assert!(!dump.exists());
    }
    std::fs::write(&cat,serde_json::to_vec(&original).unwrap()).unwrap();
    let run=Command::new(env!("CARGO_BIN_EXE_rust-interp-vm")).args(["--select-test","first","--suite-catalog"]).arg(&cat).arg(&artifact).output().unwrap();
    assert!(!run.status.success());assert!(String::from_utf8_lossy(&run.stderr).contains("selected failure"));
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

#[test]
fn single_entry_catalog_executes_only_its_selected_body() {
    let files = Files::new(); let program = fixture(true); let artifact = files.program(&program);
    for selected in [0, 1] {
        let mut single = catalog(&program);
        single.entries = vec![single.entries[selected].clone()];
        let path = files.0.join(format!("single-{selected}.json"));
        std::fs::write(&path, serde_json::to_vec(&single).unwrap()).unwrap();
        for mode in ["fresh", "prepared"] {
            let report = files.0.join(format!("single-{selected}-{mode}.json"));
            let run = command(&artifact, mode, &report, &["--suite-catalog", path.to_str().unwrap()]);
            assert_eq!(run.status.success(), selected == 1, "{}", String::from_utf8_lossy(&run.stderr));
            let report: Value = serde_json::from_slice(&std::fs::read(report).unwrap()).unwrap();
            assert_eq!(report["tests"].as_array().unwrap().len(), 1);
            assert_eq!(report["tests"][0]["name"], ["first", "second"][selected]);
            assert_eq!(report["passed"], usize::from(selected == 1));
            assert_eq!(report["failed"], usize::from(selected == 0));
        }
    }
}
