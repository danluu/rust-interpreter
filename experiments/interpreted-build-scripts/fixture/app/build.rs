use std::env;
use std::fs::{self, OpenOptions};
use std::io::Write;
use std::path::PathBuf;

fn main() {
    let out = PathBuf::from(env::var_os("OUT_DIR").expect("Cargo OUT_DIR"));
    let manifest = PathBuf::from(env::var_os("CARGO_MANIFEST_DIR").unwrap());
    assert_eq!(env::current_dir().unwrap(), manifest);
    let input: u64 = fs::read_to_string("input.txt").unwrap().trim().parse().unwrap();
    let seed: u64 = env::var("IBS_FIXTURE_SEED").unwrap_or_else(|_| "3".into()).parse().unwrap();
    let mode = if cfg!(feature = "native-shared-helper") { "native-shared" } else { "script-only" };

    #[cfg(feature = "unsupported-build-operation")]
    {
        // Deliberately before the unsupported call: a candidate must reject
        // the complete execution graph before entering main, not after this.
        fs::write(out.join("before-unsupported.txt"), b"script already executed\n").unwrap();
        let output = std::process::Command::new(env::var_os("RUSTC").unwrap())
            .arg("--version")
            .output()
            .unwrap();
        assert!(output.status.success());
        fs::write(out.join("child-version.txt"), output.stdout).unwrap();
    }

    let value = ibs_fixture_helper::transform(input, seed);
    fs::write(out.join("generated.rs"), format!(
        "pub const GENERATED_VALUE: u64 = {value};\npub const GENERATED_INPUT: u64 = {input};\npub const GENERATED_SEED: u64 = {seed};\n"
    )).unwrap();
    let mut history = OpenOptions::new().create(true).append(true).open(out.join("history.txt")).unwrap();
    writeln!(history, "input={input};seed={seed};mode={mode};value={value}").unwrap();
    history.flush().unwrap();

    // Raw context stays available for per-route binding. OUT_DIR differs
    // between independent targets and must match that route's actual output.
    let mut context = String::new();
    for key in ["OUT_DIR", "CARGO_MANIFEST_DIR", "HOST", "TARGET", "PROFILE", "OPT_LEVEL", "DEBUG", "NUM_JOBS"] {
        context.push_str(&format!("{key}={}\n", env::var(key).unwrap()));
    }
    fs::write(out.join("context.txt"), context).unwrap();

    // Preserve ordinary Cargo parsing, line order and rerun dependencies.
    println!("cargo::rerun-if-changed=build.rs");
    println!("cargo:rerun-if-changed=input.txt");
    println!("cargo::rerun-if-env-changed=IBS_FIXTURE_SEED");
    println!("cargo::rustc-check-cfg=cfg(ibs_seed_even)");
    if seed % 2 == 0 {
        println!("cargo::rustc-cfg=ibs_seed_even");
    }
    println!("cargo::rustc-env=IBS_GENERATED_CONTEXT=input={input};seed={seed};mode={mode}");
    eprintln!("build-script input={input} seed={seed} mode={mode} value={value}");
}

// QUALIFICATION_ERROR_SLOT
