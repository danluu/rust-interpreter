//! A std-only Cargo wrapper. Ordinary rustc invocations never load rustc_driver
//! in this process. Selected exports and opt-in compiler query caching exec
//! the adjacent, installed exporter.
mod wrapper_route;
mod compiler_argv;

use std::process::{Command, ExitCode};

fn main() -> ExitCode {
    let original: Vec<String> = std::env::args().collect();
    if original.len() == 2 && original[1] == "--rust-interp-stable-mono-capability" {
        // A publication-only, std-only protocol also binds this physical
        // wrapper's compiled sysroot. Normal Cargo routing stays unchanged.
        println!("stable-mono-cgu-routing-v1\n{}", env!("RUST_INTERP_SYSROOT"));
        return ExitCode::SUCCESS;
    }
    let route = match wrapper_route::route(original.clone(), &wrapper_route::Environment::read()) {
        Ok(route) if route.wrapper => route,
        Ok(_) => {
            eprintln!("rust-interp-rustc-wrapper requires Cargo's rustc argument");
            return ExitCode::from(2);
        }
        Err(error) => {
            eprintln!("{error}");
            return ExitCode::from(2);
        }
    };
    if let Err(error) = route.check_compiler(std::path::Path::new(env!("RUST_INTERP_SYSROOT"))) {
        eprintln!("{error}");
        return ExitCode::from(2);
    }
    let mut command = if route.requires_exporter() {
        let executable = match std::env::current_exe() {
            Ok(path) => path.with_file_name("rust-interp-mir-export"),
            Err(error) => {
                eprintln!("cannot locate adjacent MIR exporter: {error}");
                return ExitCode::from(127);
            }
        };
        let mut command = Command::new(executable);
        // The exporter uses the same router. Supply the original invocation
        // so sysroot/MIR flag transformations are applied exactly once.
        command.args(&original[1..]);
        command
    } else {
        if let Err(error) = compiler_argv::record("native", &route.args) {
            eprintln!("cannot retain compiler argv: {error}");
            return ExitCode::from(2);
        }
        let mut command = Command::new(&route.args[0]);
        command.args(&route.args[1..]);
        command
    };
    // Preserve cwd, environment, jobserver descriptors and Unix exit signals.
    #[cfg(unix)]
    {
        use std::os::unix::process::CommandExt;
        let error = command.exec();
        eprintln!("cannot execute compiler: {error}");
        ExitCode::from(127)
    }
    #[cfg(not(unix))]
    {
        match command.status() {
            Ok(status) => ExitCode::from(status.code().unwrap_or(1) as u8),
            Err(error) => {
                eprintln!("cannot execute compiler: {error}");
                ExitCode::from(127)
            }
        }
    }
}
