"""Load scalar artifacts while preserving the legacy CLI execution route."""
from pathlib import Path
import shutil
HERE=Path(__file__).resolve().parent

def replace(path,old,new):
    text=path.read_text()
    if text.count(old)!=1:raise RuntimeError('CLI injection anchor differs: '+old[:100])
    path.write_text(text.replace(old,new))

def inject(source):
    main=source/'crates/bytecode/src/main.rs'
    replace(main,'use std::io::Write;', '''use std::io::Write;
use rust_interp_bytecode::scalar_abi::Artifact;
enum InputArtifact { Legacy(Program), Scalar(Artifact) }''')
    replace(main,'    if version & !rust_interp_bytecode::PARTIAL_VALIDATION != rust_interp_bytecode::VERSION {',
        '''    if version & !rust_interp_bytecode::PARTIAL_VALIDATION != rust_interp_bytecode::VERSION
        && version != rust_interp_bytecode::scalar_abi::SCALAR_VERSION {''')
    replace(main,'''    let program: Program = bincode::DefaultOptions::new()
        .with_fixint_encoding()
        .with_limit(64 * 1024 * 1024)
        .reject_trailing_bytes()
        .deserialize(&bytes)?;''', '''    let artifact = if version == rust_interp_bytecode::scalar_abi::SCALAR_VERSION {
        InputArtifact::Scalar(Artifact::decode(&bytes)?)
    } else {
        InputArtifact::Legacy(bincode::DefaultOptions::new()
            .with_fixint_encoding().with_limit(64 * 1024 * 1024)
            .reject_trailing_bytes().deserialize(&bytes)?)
    };
    let program = match &artifact { InputArtifact::Legacy(p) => p, InputArtifact::Scalar(a) => &a.program };''')
    replace(main,'        let (result, profile) = execute_profiled(&program, &args, limits, engine)?;',
        '''        let (result, profile) = match &artifact {
            InputArtifact::Legacy(p) => execute_profiled(p, &args, limits, engine)?,
            InputArtifact::Scalar(a) => a.execute_profiled(&args, limits, engine)?,
        };''')
    replace(main,'        execute_with_engine(&program, &args, limits, engine)?',
        '''        match &artifact {
            InputArtifact::Legacy(p) => execute_with_engine(p, &args, limits, engine)?,
            InputArtifact::Scalar(a) => a.execute_with_engine(&args, limits, engine)?,
        }''')
    shutil.copy2(HERE/'fixture.rs',source/'crates/bytecode/src/scalar_cli_fixture.rs')
    with (source/'crates/bytecode/Cargo.toml').open('a') as out:
        out.write('\n[[bin]]\nname = "scalar-cli-fixture"\npath = "src/scalar_cli_fixture.rs"\n')
