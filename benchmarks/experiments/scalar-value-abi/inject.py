"""Install the artifact contract into an exact isolated integrated source tree."""
from pathlib import Path
import shutil
HERE=Path(__file__).resolve().parent

def replace(path,old,new):
    text=path.read_text()
    if text.count(old)!=1:raise RuntimeError('injection anchor differs: '+old[:100])
    path.write_text(text.replace(old,new))

def inject(source):
    bytecode=source/'crates/bytecode'
    shutil.copy2(HERE/'artifact.rs',bytecode/'src/scalar_abi.rs')
    shutil.copy2(HERE/'artifact_tests.rs',bytecode/'src/scalar_abi_artifact_tests.rs')
    shutil.copy2(HERE/'check_artifact.rs',bytecode/'src/scalar_abi_check.rs')
    with (bytecode/'Cargo.toml').open('a') as out:
        out.write('\n[[bin]]\nname = "scalar-abi-check"\npath = "src/scalar_abi_check.rs"\n')
    lib=bytecode/'src/lib.rs'
    replace(lib,'mod frames;','mod frames;\npub mod scalar_abi;')
    replace(lib,'''pub fn validate(program: &Program) -> Result<(), String> {
    if program.version & !PARTIAL_VALIDATION != VERSION
        || program.functions.len() > 100_000''', '''pub fn validate(program: &Program) -> Result<(), String> {
    if program.version & !PARTIAL_VALIDATION != VERSION {
        return Err("invalid bytecode header".into());
    }
    validate_structure(program)
}

pub(crate) fn validate_structure(program: &Program) -> Result<(), String> {
    if program.functions.len() > 100_000''')
