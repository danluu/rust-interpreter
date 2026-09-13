//! Explicitly ignored real-compiler controls. The caller holds the canonical
//! workload lock and supplies already-built matching exporter/compiler/VM.
//! No compiler or tool is built here; every child and artifact is retained.
use bincode::Options;
use rust_interp_bytecode::{Op, Program};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::{collections::BTreeMap, fs, path::{Path, PathBuf}, process::{Command, Output, Stdio}, time::{SystemTime, UNIX_EPOCH}};

const SOURCE: &str = include_str!("fixtures/trap_span_remap_fixture.rs");
const SCOPES: [&str; 4] = ["none", "macro", "diagnostics", "all"];
const MAPPED: &str = "/trap-remap-source";

fn sha(bytes: &[u8]) -> String { format!("{:x}", Sha256::digest(bytes)) }
fn write_json(path: &Path, value: &Value) { fs::write(path, serde_json::to_vec_pretty(value).unwrap()).unwrap(); }
fn now() -> f64 { SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_secs_f64() }
fn required(name: &str) -> PathBuf {
    fs::canonicalize(std::env::var_os(name).unwrap_or_else(|| panic!("{name} is required"))).unwrap()
}

struct Run {
    root: PathBuf,
    exporter: PathBuf,
    rustc: PathBuf,
    vm: PathBuf,
    sysroot: PathBuf,
    native_sysroot: PathBuf,
    backend_jobs: String,
    frozen: BTreeMap<PathBuf, String>,
    next: usize,
}
impl Run {
    fn new(name: &str) -> Self {
        let root = required("RUST_INTERP_TEST_ARTIFACT_DIR").join(name);
        fs::create_dir(&root).expect("fresh retained test directory required");
        let exporter = required("RUST_INTERP_TEST_EXPORTER");
        let rustc = required("RUST_INTERP_TEST_RUSTC");
        let vm = required("RUST_INTERP_TEST_VM");
        let sysroot = required("RUST_INTERP_TEST_STD_SYSROOT");
        let source = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("tests/fixtures/trap_span_remap_fixture.rs");
        assert_eq!(fs::read(&source).unwrap(), SOURCE.as_bytes());
        let frozen = [exporter.clone(), rustc.clone(), vm.clone(), source,
            PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("tests/trap_span_remap.rs")].into_iter().map(|path| {
                let path = fs::canonicalize(path).unwrap();
                let digest = sha(&fs::read(&path).unwrap()); (path, digest)
            }).collect();
        let native_sysroot=rustc.parent().unwrap().parent().unwrap().to_path_buf();
        // Keep the custom compiler's existing default. Stock rustc callers
        // explicitly select two codegen units for these tiny native controls.
        let backend_jobs = std::env::var("RUST_INTERP_TEST_BACKEND_JOBS_FLAG")
            .unwrap_or_else(|_| "--jobs-backend=2".into());
        assert!(matches!(backend_jobs.as_str(), "--jobs-backend=2" | "-Ccodegen-units=2"),
            "unsupported backend-jobs test setting");
        let mut run = Self { root, exporter, rustc, vm, sysroot, native_sysroot, backend_jobs, frozen, next: 0 };
        let version = run.command(run.rustc.clone(), vec!["-vV".into()], None);
        success(&version);
        let caps = run.command(run.exporter.clone(), vec!["--rust-interp-capabilities".into()], None);
        success(&caps);
        let caps: Value = serde_json::from_slice(&caps.stdout).unwrap();
        let actual = run.command(run.rustc.clone(), vec!["--print".into(), "sysroot".into()], None);
        success(&actual);
        run.native_sysroot=fs::canonicalize(String::from_utf8(actual.stdout).unwrap().trim()).unwrap();
        assert_eq!(fs::canonicalize(caps["compiler_sysroot"].as_str().unwrap()).unwrap(),run.native_sysroot);
        write_json(&run.root.join("inputs.json"), &json!({"files":run.frozen,"metadata_sysroot":run.sysroot,
            "native_sysroot":run.native_sysroot,"backend_jobs_flag":run.backend_jobs,"capabilities":caps}));
        run
    }
    fn guard(&self) {
        for (path, expected) in &self.frozen { assert_eq!(&sha(&fs::read(path).unwrap()), expected, "{}", path.display()); }
    }
    fn command(&mut self, executable: PathBuf, args: Vec<String>, output: Option<&Path>) -> Output {
        self.guard();
        let directory = self.root.join(format!("command-{:03}", self.next)); self.next += 1;
        fs::create_dir(&directory).unwrap();
        let sources: BTreeMap<_,_> = args.iter().filter(|arg| arg.ends_with(".rs")).map(|arg| {
            let bytes = fs::read(arg).unwrap();
            fs::write(directory.join("input.rs"), &bytes).unwrap();
            (arg.clone(), sha(&bytes))
        }).collect();
        let mut command = Command::new(&executable);
        command.args(&args).current_dir(&self.root).stdout(Stdio::piped()).stderr(Stdio::piped());
        for (key, _) in std::env::vars_os() {
            let key = key.to_string_lossy();
            if key.starts_with("RUST_INTERP_") || key.starts_with("CARGO_") ||
                ["RUSTFLAGS", "RUSTC", "RUSTDOC", "RUSTC_WRAPPER", "RUSTC_WORKSPACE_WRAPPER"].contains(&key.as_ref()) {
                command.env_remove(key.as_ref());
            }
        }
        if let Some(output) = output { command.env("RUST_INTERP_OUTPUT", output); }
        let child = command.spawn().unwrap();
        let mut receipt = json!({"pid":child.id(),"parent_pid":std::process::id(),"cwd":self.root,
            "executable":executable,"args":args,"source_sha256":sources,"output":output,"started_at":now()});
        // Wait the exact owned child even when writing its first receipt fails.
        let published = fs::write(directory.join("receipt.json"), serde_json::to_vec_pretty(&receipt).unwrap());
        let result = child.wait_with_output().unwrap();
        published.unwrap();
        fs::write(directory.join("stdout"), &result.stdout).unwrap();
        fs::write(directory.join("stderr"), &result.stderr).unwrap();
        receipt["returncode"] = json!(result.status.code()); receipt["finished_at"] = json!(now());
        write_json(&directory.join("receipt.json"), &receipt); self.guard(); result
    }
    fn flags(&self, source: &Path, scope: &str, linked: bool) -> Vec<String> {
        let mut flags = vec!["--edition=2024".into(), "--crate-name=trap_span_fixture".into(),
            "-Copt-level=0".into(), "-Cdebuginfo=0".into(), "-Cdebug-assertions=yes".into(),
            "-Coverflow-checks=yes".into(), "-Zmir-opt-level=0".into(), "--error-format=json".into(),
            "-Zunstable-options".into(), self.backend_jobs.clone(), "--sysroot".into(),
            (if linked {&self.native_sysroot} else {&self.sysroot}).display().to_string(), source.display().to_string()];
        if scope != "none" {
            flags.push(format!("--remap-path-prefix={}={MAPPED}", source.parent().unwrap().display()));
            flags.push(format!("--remap-path-scope={scope}"));
        }
        flags
    }
    fn compile(&mut self, source: &Path, scope: &str, label: &str, export: bool, linked: bool) -> (Output, PathBuf) {
        let output = self.root.join(format!("{label}.rbc"));
        let mut flags = self.flags(source, scope, linked);
        let artifact = self.root.join(format!("{label}.{}", if linked { "native" } else { "rmeta" }));
        flags.extend([format!("--crate-type={}", if linked { "bin" } else { "lib" }),
            format!("--emit={}", if linked { "link" } else { "metadata" }), "-o".into(), artifact.display().to_string()]);
        if linked { flags.push("--cfg=native".into()); }
        if export {
            // These are the optimized MIR bodies actually consumed by export.
            let dump = self.root.join(format!("{label}.mir")); fs::create_dir(&dump).unwrap();
            flags.extend(["-Zdump-mir=fast_path|slow_path".into(), format!("-Zdump-mir-dir={}",dump.display()),
                "-Zdump-mir-exclude-pass-number".into()]);
        }
        let result = self.command(if export { self.exporter.clone() } else { self.rustc.clone() }, flags,
            export.then_some(output.as_path()));
        (result, if export { output } else { artifact })
    }
}
fn success(result: &Output) {
    assert!(result.status.success(), "{}", String::from_utf8_lossy(&result.stderr));
}
fn rows(result: &Output) -> Vec<Vec<String>> {
    success(result);
    String::from_utf8(result.stdout.clone()).unwrap().lines().map(|line| line.split('\t').map(str::to_owned).collect()).collect()
}
fn diagnostics(result: &Output) -> Vec<Value> {
    String::from_utf8(result.stderr.clone()).unwrap().lines().filter_map(|line|
        serde_json::from_str::<Value>(line).ok()).filter(|value| value["$message_type"] == "diagnostic").collect()
}
fn has_source_span(value: &Value, filename: &str) -> bool {
    match value {
        Value::Object(fields) => {
            (fields.get("file_name").and_then(Value::as_str)==Some(filename)
                && fields.get("byte_start").is_some_and(Value::is_number)
                && fields.get("byte_end").is_some_and(Value::is_number))
                || fields.values().any(|child|has_source_span(child,filename))
        }
        Value::Array(items) => items.iter().any(|child|has_source_span(child,filename)),
        _ => false,
    }
}
fn program(path: &Path) -> Program {
    let bytes = fs::read(path).unwrap();
    let p: Program = bincode::DefaultOptions::new().with_fixint_encoding().with_limit(64*1024*1024)
        .reject_trailing_bytes().deserialize(&bytes).unwrap();
    assert_eq!(p.version, rust_interp_bytecode::VERSION); rust_interp_bytecode::validate(&p).unwrap(); p
}
fn assert_both_lowering_paths(dump: &Path) {
    for (function, marker) in [("fast_path", "fast trap"), ("slow_path", "slow trap")] {
        let files: Vec<_> = fs::read_dir(dump).unwrap().map(|entry|entry.unwrap().path()).filter(|path| {
            let name=path.file_name().unwrap().to_string_lossy();
            name.contains(&format!(".{function}.")) && name.ends_with(".runtime-optimized.after.mir")
        }).collect();
        assert_eq!(files.len(),1,"one actual optimized MIR dump required for {function}");
        let text=fs::read_to_string(&files[0]).unwrap();
        let block=text.split("    bb0: {\n").nth(1).unwrap().split("\n    }").next().unwrap();
        let lines: Vec<_> = block.lines().map(str::trim).filter(|line|!line.is_empty()&&!line.starts_with("//")).collect();
        let call=lines.iter().position(|line|line.contains(marker)&&line.contains(" -> ")).unwrap();
        assert_eq!(call+1,lines.len(),"panic must terminate this exact block");
        if function=="fast_path" {
            assert!(lines[..call].iter().all(|line|line.starts_with("StorageLive(")||line.starts_with("StorageDead(")||*line=="nop;"),
                "fast fixture changed: its statements no longer prove panic_preparation");
        } else {
            assert!(lines[..call].iter().any(|line|line.starts_with("(*_1) = const 29_u64;")),
                "projected store must be in the panic's own block, rejecting panic_preparation");
        }
    }
}

#[test]
#[ignore = "requires matching built tools, retained directory and caller-held canonical workload lock"]
fn trap_artifacts_follow_macro_scope_and_native_observables() {
    let mut run = Run::new("trap-artifact-scopes");
    let mut artifacts = BTreeMap::new();
    for root in ["first", "second"] {
        let directory = run.root.join(root); fs::create_dir(&directory).unwrap();
        let source = directory.join("fixture.rs"); fs::write(&source, SOURCE).unwrap();
        for scope in SCOPES {
            let label = format!("{root}-{scope}");
            let (native, binary) = run.compile(&source, scope, &format!("{label}-native"), false, true); success(&native);
            let (export, bytecode) = run.compile(&source, scope, &label, true, false); success(&export);
            assert_both_lowering_paths(&run.root.join(format!("{label}.mir")));
            let p = program(&bytecode);
            let expected_file = if ["macro", "all"].contains(&scope) { format!("{MAPPED}/fixture.rs") } else { source.display().to_string() };
            for (case, function) in [(0, "fast_path"), (1, "slow_path")] {
                let native = rows(&run.command(binary.clone(), vec![case.to_string()], None));
                assert_eq!(native[0][0], "panic"); assert_eq!(native[0][1], expected_file);
                assert_eq!(native[1], vec!["cell".to_owned(), (if case==0 {"0"} else {"29"}).to_owned()]);
                let functions: Vec<_> = p.functions.iter().filter(|f| f.name==format!("{function}[]")).collect();
                assert_eq!(functions.len(),1); let f = functions[0];
                let traps: Vec<_> = f.code.iter().filter_map(|op| if let Op::Trap{message}=op {Some(message)} else {None}).collect();
                assert_eq!(traps.len(),1);
                let location = format!("core::panicking::panic at {}:{}:{}: ", expected_file,native[0][2],native[0][3]);
                assert!(traps[0].starts_with(&location), "{} vs {location}", traps[0]);
                assert!(fs::read(&bytecode).unwrap().windows(traps[0].len()).any(|w|w==traps[0].as_bytes()));
                if case == 0 { assert_eq!(f.code.len(),1,"fast block must contain only its Trap"); }
                else { assert!(f.code.iter().take_while(|op| !matches!(op,Op::Trap{..})).any(|op|matches!(op,Op::Store{..})),"projected write must survive before Trap"); }
                let vm = run.command(run.vm.clone(), vec![bytecode.display().to_string(),case.to_string()],None);
                assert!(!vm.status.success()); assert_eq!(vm.stdout,b"");
                assert_eq!(String::from_utf8(vm.stderr).unwrap(),format!("rust-interp-vm: guest trap: {} in {}\n",traps[0],f.name));
            }
            let native = rows(&run.command(binary,vec!["2".into()],None));
            assert_eq!(native[0],vec!["file".to_owned(),expected_file.clone()]);
            assert_eq!(native[1][0],"caller"); assert_eq!(native[1][1],expected_file);
            let vm = run.command(run.vm.clone(),vec![bytecode.display().to_string(),"2".into()],None); success(&vm);
            assert_eq!(String::from_utf8(vm.stdout).unwrap(),format!("{}\n",native[2][1]));
            artifacts.insert((root,scope),fs::read(&bytecode).unwrap());
            assert_eq!(fs::read(&source).unwrap(),SOURCE.as_bytes());
        }
        assert_eq!(artifacts[&(root,"none")],artifacts[&(root,"diagnostics")],"diagnostic-only remaps cannot enter artifacts");
        assert_eq!(artifacts[&(root,"macro")],artifacts[&(root,"all")]);
        assert_ne!(artifacts[&(root,"none")],artifacts[&(root,"macro")],"macro remapping has real observable semantics");
    }
    for scope in ["macro","all"] { assert_eq!(artifacts[&("first",scope)],artifacts[&("second",scope)]); }
    for scope in ["none","diagnostics"] { assert_ne!(artifacts[&("first",scope)],artifacts[&("second",scope)]); }
    run.guard();
}

#[test]
#[ignore = "requires matching built tools, retained directory and caller-held canonical workload lock"]
fn uncalled_errors_keep_full_native_diagnostics_for_every_scope() {
    let mut run=Run::new("trap-uncalled-diagnostics");
    let source=run.root.join("fixture.rs");
    let original="#![allow(dead_code)]\npub fn rust_interp_entry() -> u64 { 7 }\n";
    for scope in SCOPES {
        for (kind,invalid,code) in [
            ("type","fn uncalled() -> u64 { false }\n","E0308"),
            ("borrow","fn uncalled() -> &'static u64 { let value=1; &value }\n","E0515"),
            ("const","const BAD: u64 = panic!(\"uncalled const\");\n","E0080"),
        ] {
            fs::write(&source,format!("{original}{invalid}")).unwrap();
            let label=format!("{scope}-{kind}");
            let (native,_)=run.compile(&source,scope,&format!("{label}-native"),false,false);
            let (export,artifact)=run.compile(&source,scope,&label,true,false);
            assert!(!native.status.success()); assert!(!export.status.success()); assert!(!artifact.exists());
            let expected=diagnostics(&native); let actual=diagnostics(&export);
            assert!(expected.iter().any(|d|d["code"]["code"]==code));
            // Includes rendered, messages, children, suggestions, spans and snippets.
            // Nothing from either actual compiler output is replaced or normalized.
            assert_eq!(actual,expected);
            let filename=if ["diagnostics","all"].contains(&scope) {format!("{MAPPED}/fixture.rs")} else {source.display().to_string()};
            // E0080's primary span is in core's panic macro. The application
            // callsite is a real nested expansion span, not a top-level span.
            assert!(actual.iter().any(|diagnostic|has_source_span(diagnostic,&filename)));
            fs::write(&source,original).unwrap();
            let (native,_)=run.compile(&source,scope,&format!("{label}-restored-native"),false,false);success(&native);
            let (export,artifact)=run.compile(&source,scope,&format!("{label}-restored"),true,false);success(&export);
            let executed=run.command(run.vm.clone(),vec![artifact.display().to_string()],None);success(&executed);
            assert_eq!(executed.stdout,b"7\n");
        }
    }
    assert_eq!(fs::read(&source).unwrap(),original.as_bytes()); run.guard();
}
