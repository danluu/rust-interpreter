use bincode::Options;
use rust_interp_bytecode::scalar_abi::Artifact;
use rust_interp_bytecode::{Engine, Limits, Program, execute_profiled, execute_with_engine};
use std::io::Write;
enum InputArtifact {
    Legacy(Program),
    Scalar(Artifact),
}

fn run() -> Result<(), Box<dyn std::error::Error>> {
    let mut args = std::env::args().skip(1);
    let mut limits = Limits::default();
    let mut engine = Engine::Interpreter;
    let mut profile_path = None;
    let mut path = args.next().ok_or(
        "usage: rust-interp-vm [--engine interpreter|jit] [--jit-native-calls] [--jit-native-call-stubs] [--jit-persistent-registers] [--jit-resumable-calls] [--jit-code-dump NEW_DIRECTORY] [--instruction-limit N] [--allocation-limit N] [--profile NEW_JSON_PATH] PROGRAM [unsigned integer arguments ...]",
    )?;
    loop {
        match path.as_str() {
            "--jit-native-calls" => limits.jit_native_calls = true,
            "--jit-native-call-stubs" => limits.jit_native_call_stubs = true,
            "--jit-persistent-registers" => limits.jit_persistent_registers = true,
            "--jit-resumable-calls" => limits.jit_resumable_calls = true,
            "--jit-code-dump" => {
                if limits.jit_code_dump.is_some() {
                    return Err("duplicate native code dump path".into());
                }
                limits.jit_code_dump =
                    Some(args.next().ok_or("missing native code dump path")?.into());
            }
            "--profile" => {
                if profile_path.is_some() {
                    return Err("duplicate profile path".into());
                }
                profile_path = Some(args.next().ok_or("missing profile path")?);
            }
            "--allocation-limit" => {
                limits.allocations = args.next().ok_or("missing allocation limit")?.parse()?;
                if limits.allocations > rust_interp_bytecode::MAX_ALLOCATION_LIMIT {
                    return Err(format!(
                        "live allocation limit exceeds supported maximum of {}",
                        rust_interp_bytecode::MAX_ALLOCATION_LIMIT
                    )
                    .into());
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
    if version & !rust_interp_bytecode::PARTIAL_VALIDATION != rust_interp_bytecode::VERSION
        && version != rust_interp_bytecode::scalar_abi::SCALAR_VERSION
    {
        return Err("bytecode version mismatch; re-export with the matching engine".into());
    }
    let artifact = if version == rust_interp_bytecode::scalar_abi::SCALAR_VERSION {
        InputArtifact::Scalar(Artifact::decode(&bytes)?)
    } else {
        InputArtifact::Legacy(
            bincode::DefaultOptions::new()
                .with_fixint_encoding()
                .with_limit(64 * 1024 * 1024)
                .reject_trailing_bytes()
                .deserialize(&bytes)?,
        )
    };
    let program = match &artifact {
        InputArtifact::Legacy(p) => p,
        InputArtifact::Scalar(a) => &a.program,
    };
    if program.version & rust_interp_bytecode::PARTIAL_VALIDATION != 0 {
        eprintln!(
            "rust-interp-vm: PARTIAL validation; unselected bodies may contain compile errors"
        );
    }
    let args = args
        .map(|s| s.parse::<u128>())
        .collect::<Result<Vec<_>, _>>()?;
    let result = if let Some(path) = profile_path {
        let file = std::fs::OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(path)?;
        let (result, profile) = match &artifact {
            InputArtifact::Legacy(p) => execute_profiled(p, &args, limits, engine)?,
            InputArtifact::Scalar(a) => a.execute_profiled(&args, limits, engine)?,
        };
        let mut writer = std::io::BufWriter::new(file);
        serde_json::to_writer(&mut writer, &profile)?;
        writer.flush()?;
        result
    } else {
        match &artifact {
            InputArtifact::Legacy(p) => execute_with_engine(p, &args, limits, engine)?,
            InputArtifact::Scalar(a) => a.execute_with_engine(&args, limits, engine)?,
        }
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
        eprintln!(
            "jit_resumable_calls={} jit_resumable_returns={}",
            result.jit_resumable_calls, result.jit_resumable_returns
        );
        eprintln!(
            "jit_tree_entries={} jit_tree_calls={} jit_tree_instructions={} jit_tree_bytes={} jit_tree_operations={} jit_tree_compiled_functions={} jit_tree_declined_functions={} jit_tree_compile_ns={}",
            result.jit_tree_entries,
            result.jit_tree_calls,
            result.jit_tree_instructions,
            result.jit_tree_bytes,
            result.jit_tree_operations,
            result.jit_tree_compiled_functions,
            result.jit_tree_declined_functions,
            result.jit_tree_compile_nanos
        );
        eprintln!(
            "jit_call_stubs={} jit_stub_calls={}",
            result.jit_call_stubs, result.jit_stub_calls
        );
        eprintln!(
            "jit_register_functions={} jit_register_pairs={} jit_liveness_declines={}",
            result.jit_register_functions, result.jit_register_pairs, result.jit_liveness_declines
        );
    }
    Ok(())
}
fn main() {
    if let Err(error) = run() {
        eprintln!("rust-interp-vm: {error}");
        std::process::exit(1);
    }
}
