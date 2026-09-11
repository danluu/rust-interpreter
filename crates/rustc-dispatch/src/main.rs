//! Append explicitly requested backend flags after Cargo has resolved its own
//! configuration. This preserves target-specific and conditional rustflags.
use std::ffi::OsString;
use std::process::{Command, ExitCode};

fn main() -> ExitCode {
    let Some(compiler) = std::env::var_os("RUST_INTERP_REAL_RUSTC") else {
        eprintln!("rustc-dispatch: RUST_INTERP_REAL_RUSTC is required");
        return ExitCode::from(2);
    };
    let mut arguments: Vec<OsString> = std::env::args_os().skip(1).collect();
    let is_target = arguments
        .iter()
        .any(|arg| arg == "--target" || arg.to_string_lossy().starts_with("--target="));
    if std::env::var_os("RUST_INTERP_DISPATCH_TARGET_ONLY").is_none() || is_target {
        let flags = match std::env::var("RUST_INTERP_DISPATCH_FLAGS") {
            Ok(flags) => flags,
            Err(error) => {
                eprintln!("rustc-dispatch: missing or invalid flags: {error}");
                return ExitCode::from(2);
            }
        };
        arguments.extend(
            flags
                .split('\x1f')
                .filter(|s| !s.is_empty())
                .map(OsString::from),
        );
    }
    // Installed as RUSTC, so Cargo preserves its normal wrapper chain outside
    // this process, as well as its resolved rustflags inside the argument list.
    let mut command = Command::new(compiler);
    command.args(arguments);
    #[cfg(unix)]
    {
        use std::os::unix::process::CommandExt;
        let error = command.exec();
        eprintln!("rustc-dispatch: cannot execute compiler: {error}");
        ExitCode::from(127)
    }
    #[cfg(not(unix))]
    {
        match command.status() {
            Ok(status) => ExitCode::from(status.code().unwrap_or(1) as u8),
            Err(error) => {
                eprintln!("rustc-dispatch: cannot execute compiler: {error}");
                ExitCode::from(127)
            }
        }
    }
}
