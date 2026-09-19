use bincode::Options;
use rust_interp_bytecode::{Engine, Limits, Program, execute_profiled, execute_with_engine};
use std::io::Write;
use sha2::{Digest, Sha256};
mod suite;
#[cfg(all(feature="jit-template-session",target_arch="aarch64",target_os="macos"))]
mod session_client;

fn run() -> Result<(), Box<dyn std::error::Error>> {
    let mut args = std::env::args().skip(1);
    let mut limits = Limits::default();
    let mut engine = Engine::Interpreter;
    let mut profile_path = None;
    let mut profile_test = None;
    let mut selection_requires_profile = false;
    let mut isolated_batch = None;
    let mut suite_report = None;
    let mut suite_catalog = None;
    let mut suite_workers = None;
    let mut template_session = None;
    let mut path = args.next().ok_or(
        "usage: rust-interp-vm [--engine interpreter|jit] [--jit-native-calls] [--jit-native-call-stubs] [--jit-persistent-registers] [--jit-resumable-calls] [--jit-scalar-calls] [--jit-indirect-calls] [--jit-template-session READY_JSON] [--jit-code-dump NEW_DIRECTORY [--jit-operation-map]] [--guest-descriptor-io] [--guest-getcwd] [--instruction-limit N] [--allocation-limit N] [--select-test EXACT_NAME --suite-catalog CATALOG] [--profile NEW_JSON_PATH [--profile-test EXACT_NAME --suite-catalog CATALOG]] [--isolated-batch fresh|prepared --suite-report NEW_JSON_PATH [--suite-workers N]] PROGRAM [unsigned integer arguments ...]",
    )?;
    loop {
        match path.as_str() {
            "--jit-template-session" => {
                if template_session.is_some() {return Err("duplicate template session path".into());}
                template_session=Some(args.next().ok_or("missing template session readiness path")?);
            }
            "--isolated-batch" => {
                if isolated_batch.is_some() { return Err("duplicate isolated batch mode".into()); }
                isolated_batch = Some(match args.next().as_deref() {
                    Some("fresh") => suite::Mode::Fresh,
                    Some("prepared") => suite::Mode::Prepared,
                    _ => return Err("isolated batch mode must be fresh or prepared".into()),
                });
            }
            "--suite-report" => {
                if suite_report.is_some() { return Err("duplicate suite report path".into()); }
                suite_report = Some(args.next().ok_or("missing suite report path")?);
            }
            "--suite-workers" => {
                if suite_workers.is_some() { return Err("duplicate suite worker count".into()); }
                let workers: usize = args.next().ok_or("missing suite worker count")?.parse()?;
                if !(1..=64).contains(&workers) { return Err("suite workers must be in 1..64".into()); }
                suite_workers = Some(workers);
            }
            "--suite-catalog" => {
                if suite_catalog.is_some() { return Err("duplicate suite catalog path".into()); }
                suite_catalog = Some(args.next().ok_or("missing suite catalog path")?);
            }
            "--guest-getcwd" => {
                if limits.guest_getcwd { return Err("duplicate guest getcwd option".into()); }
                limits.guest_getcwd = true;
            }
            "--guest-descriptor-io" => {
                if limits.guest_descriptor_io { return Err("duplicate guest descriptor I/O option".into()); }
                limits.guest_descriptor_io = true;
            }
            "--jit-native-calls" => limits.jit_native_calls = true,
            "--jit-native-call-stubs" => limits.jit_native_call_stubs = true,
            "--jit-indirect-calls" => limits.jit_indirect_calls = true,
            "--jit-persistent-registers" => limits.jit_persistent_registers = true,
            "--jit-resumable-calls" => limits.jit_resumable_calls = true,
            "--jit-scalar-calls" => limits.jit_scalar_calls = true,
            "--jit-operation-map" => {
                if limits.jit_operation_map { return Err("duplicate operation map option".into()); }
                limits.jit_operation_map = true;
            }
            "--jit-code-dump" => {
                if limits.jit_code_dump.is_some() { return Err("duplicate native code dump path".into()); }
                limits.jit_code_dump = Some(args.next().ok_or("missing native code dump path")?.into());
            }
            "--profile" => {
                if profile_path.is_some() { return Err("duplicate profile path".into()); }
                profile_path = Some(args.next().ok_or("missing profile path")?);
            }
            "--profile-test" | "--select-test" => {
                if profile_test.is_some() { return Err("duplicate test selection".into()); }
                selection_requires_profile = path == "--profile-test";
                profile_test = Some(args.next().ok_or("missing exact test name")?);
            }
            "--allocation-limit" => {
                limits.allocations = args.next().ok_or("missing allocation limit")?.parse()?;
                if limits.allocations > rust_interp_bytecode::MAX_ALLOCATION_LIMIT {
                    return Err(format!("live allocation limit exceeds supported maximum of {}",
                        rust_interp_bytecode::MAX_ALLOCATION_LIMIT).into());
                }
            }
            "--instruction-limit" => {
                limits.instructions = args.next().ok_or("missing instruction limit")?.parse()?
            }
            "--engine" => {
                engine = match args.next().as_deref() {
                    Some("interpreter") => Engine::Interpreter,
                    Some("jit") => Engine::Jit,
                    _ => return Err("unknown execution engine".into()),
                }
            }
            _ => break,
        }
        path = args.next().ok_or("missing program path")?;
    }
    if let Some(ready)=template_session {
        if engine!=Engine::Jit || !matches!(isolated_batch,Some(suite::Mode::Prepared)) || suite_workers!=Some(2)
            || suite_catalog.is_none() || suite_report.is_none() || !limits.jit_resumable_calls
            || limits.jit_native_calls || limits.jit_native_call_stubs || limits.jit_code_dump.is_some()
            || limits.jit_operation_map || limits.guest_descriptor_io || limits.guest_getcwd
            || profile_path.is_some() || profile_test.is_some() || args.next().is_some() {
            return Err("template sessions require a prepared two-worker resumable JIT suite with catalog/report and no additional execution options".into());
        }
        #[cfg(all(feature="jit-template-session",target_arch="aarch64",target_os="macos"))]
        {
            session_client::run(&ready,&path,suite_catalog.as_deref().unwrap(),suite_report.as_deref().unwrap(),&limits)?;
            println!("0");return Ok(());
        }
        #[cfg(not(all(feature="jit-template-session",target_arch="aarch64",target_os="macos")))]
        {let _=ready;return Err("template session client requires the explicit jit-template-session feature on AArch64 macOS".into());}
    }
    if std::fs::metadata(&path)?.len() > 64 * 1024 * 1024 {
        return Err("artifact exceeds 64 MiB".into());
    }
    let bytes = std::fs::read(path)?;
    let version = u32::from_le_bytes(
        bytes
            .get(..4)
            .ok_or("truncated bytecode header")?
            .try_into()?,
    );
    if version & !rust_interp_bytecode::PARTIAL_VALIDATION != rust_interp_bytecode::VERSION {
        return Err("bytecode version mismatch; re-export with the matching engine".into());
    }
    let mut program: Program = bincode::DefaultOptions::new()
        .with_fixint_encoding()
        .with_limit(64 * 1024 * 1024)
        .reject_trailing_bytes()
        .deserialize(&bytes)?;
    if program.version & rust_interp_bytecode::PARTIAL_VALIDATION != 0 {
        eprintln!(
            "rust-interp-vm: PARTIAL validation; unselected bodies may contain compile errors"
        );
    }
    let args = args
        .map(|s| s.parse::<u128>())
        .collect::<Result<Vec<_>, _>>()?;
    if isolated_batch.is_some() != suite_report.is_some() {
        return Err("isolated batch mode and suite report must be supplied together".into());
    }
    if profile_test.is_some() && ((selection_requires_profile && profile_path.is_none()) || suite_catalog.is_none()
        || isolated_batch.is_some() || !args.is_empty()) {
        return Err(if selection_requires_profile {
            "--profile-test requires --profile and --suite-catalog without an isolated batch or entry arguments"
        } else {
            "--select-test requires --suite-catalog without an isolated batch or entry arguments"
        }.into());
    }
    if suite_catalog.is_some() && isolated_batch.is_none() && profile_test.is_none() {
        return Err("--suite-catalog requires an isolated batch, --profile-test or --select-test".into());
    }
    let catalog_bytes = if let Some(path) = suite_catalog {
        if std::fs::metadata(&path)?.len() > 8 * 1024 * 1024 {
            return Err("entry catalog exceeds 8 MiB".into());
        }
        Some(std::fs::read(path)?)
    } else { None };
    let catalog = catalog_bytes.as_ref().map(|bytes|
        serde_json::from_slice::<rust_interp_bytecode::EntryCatalog>(bytes)).transpose()?;
    if let Some(name) = profile_test {
        let catalog = catalog.as_ref().unwrap();
        let entries = catalog.validated_entries(&program, &bytes)?;
        let selected = entries.iter().find(|(entry, _)| *entry == name)
            .ok_or("test name is absent from the exact entry catalog")?.1;
        rust_interp_bytecode::validate(&program)?;
        // Record the selection against the original artifact before changing
        // only the in-memory entry. The bytecode file and all functions stay
        // intact. Each command starts fresh guest state and a fresh JIT owner.
        let prefix=if selection_requires_profile {"rust-interp-profile-selection"} else {"rust-interp-test-selection"};
        eprintln!("{prefix}: {}", serde_json::json!({
            "schema_version":1,"name":name,"function":selected,"original_entry":program.entry,
            "artifact_sha256":format!("{:x}",Sha256::digest(&bytes)),
            "catalog_sha256":format!("{:x}",Sha256::digest(catalog_bytes.as_ref().unwrap())),
            "scope":"one catalog test with fresh guest state and JIT; diagnostic execution"
        }));
        program.entry = selected;
    }
    if suite_workers.is_some() && isolated_batch.is_none() {
        return Err("suite workers require an isolated batch".into());
    }
    if let Some(mode) = isolated_batch {
        if engine != Engine::Jit || !limits.jit_resumable_calls || limits.jit_native_calls
            || limits.jit_native_call_stubs || profile_path.is_some() || limits.jit_code_dump.is_some()
            || limits.jit_operation_map || !args.is_empty()
        {
            return Err("isolated batches require resumable JIT execution without tree/stub, profile, code dump or entry arguments".into());
        }
        suite::run(&program, mode, &limits, suite_report.as_deref().unwrap(), catalog.as_ref(), &bytes, suite_workers.unwrap_or(1))?;
        println!("0");
        return Ok(());
    }
    let result = if let Some(path) = profile_path {
        let file = std::fs::OpenOptions::new().write(true).create_new(true).open(path)?;
        let (result, profile) = execute_profiled(&program, &args, limits, engine)?;
        let mut writer = std::io::BufWriter::new(file);
        serde_json::to_writer(&mut writer, &profile)?;
        writer.flush()?;
        result
    } else {
        execute_with_engine(&program, &args, limits, engine)?
    };
    println!("{}", result.value);
    if std::env::var_os("RUST_INTERP_VM_STATS").is_some() {
        eprintln!(
            "instructions={} peak_guest_memory={}",
            result.instructions, result.peak_memory
        );
        eprintln!(
            "jit_bytes={} jit_operations={} jit_compile_ns={} jit_instructions={} jit_entries={} jit_compiled_functions={} jit_declined_functions={}",
            result.jit_bytes,
            result.jit_operations,
            result.jit_compile_nanos,
            result.jit_instructions,
            result.jit_entries,
            result.jit_compiled_functions,
            result.jit_declined_functions
        );
        eprintln!("jit_resumable_calls={} jit_resumable_returns={}", result.jit_resumable_calls, result.jit_resumable_returns);
        eprintln!("jit_tree_entries={} jit_tree_calls={} jit_tree_instructions={} jit_tree_bytes={} jit_tree_operations={} jit_tree_compiled_functions={} jit_tree_declined_functions={} jit_tree_compile_ns={}",
            result.jit_tree_entries, result.jit_tree_calls, result.jit_tree_instructions,
            result.jit_tree_bytes, result.jit_tree_operations, result.jit_tree_compiled_functions,
            result.jit_tree_declined_functions, result.jit_tree_compile_nanos);
        eprintln!("jit_call_stubs={} jit_stub_calls={}", result.jit_call_stubs, result.jit_stub_calls);
        eprintln!("jit_register_functions={} jit_register_pairs={} jit_liveness_declines={}",
            result.jit_register_functions, result.jit_register_pairs, result.jit_liveness_declines);
    }
    Ok(())
}
fn main() {
    if let Err(error) = run() {
        eprintln!("rust-interp-vm: {error}");
        std::process::exit(1);
    }
}
