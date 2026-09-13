//! Optional qualification evidence at the final compiler-call boundary.
//! One create-new file per process/role avoids concurrent append ambiguity.
use std::io::Write;
use std::path::Path;

pub fn record(role: &str, args: &[String]) -> std::io::Result<()> {
    let Some(directory) = std::env::var_os("RUST_INTERP_COMPILER_ARGV_RECORD_DIR") else {
        return Ok(());
    };
    let directory = Path::new(&directory);
    if !directory.is_absolute() || directory.canonicalize()? != directory || !directory.is_dir() {
        return Err(std::io::Error::other("compiler argv directory must be an ordinary absolute directory"));
    }
    let cwd = std::env::current_dir()?;
    let cwd = cwd.to_str().ok_or_else(|| std::io::Error::other("compiler argv cwd is not UTF-8"))?;
    let fields = ["rust-interp-compiler-argv-v1", role, env!("RUST_INTERP_SYSROOT"), cwd];
    let mut payload = Vec::new();
    for field in fields.into_iter().chain(args.iter().map(String::as_str)) {
        if field.contains('\0') {
            return Err(std::io::Error::other("compiler argv field contains NUL"));
        }
        payload.extend_from_slice(field.as_bytes());
        payload.push(0);
    }
    let path = directory.join(format!("{role}-{}.argv", std::process::id()));
    let mut file = std::fs::OpenOptions::new().write(true).create_new(true).open(path)?;
    file.write_all(&payload)
}
