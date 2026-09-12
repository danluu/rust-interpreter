//! Verify original artifact roundtrips without executing a guest.
use rust_interp_bytecode::scalar_abi::{Artifact, MAX_ARTIFACT_BYTES};
fn main()->Result<(),Box<dyn std::error::Error>> {
    let path=std::env::args().nth(1).ok_or("usage: scalar-abi-check PROGRAM")?;
    if std::fs::metadata(&path)?.len()>MAX_ARTIFACT_BYTES {return Err("artifact exceeds limit".into());}
    let bytes=std::fs::read(path)?;let artifact=Artifact::decode(&bytes)?;
    if artifact.encode()?!=bytes {return Err("artifact roundtrip changed bytes".into());}
    println!("version={} functions={} identical=true",artifact.program.version,artifact.program.functions.len());
    Ok(())
}
