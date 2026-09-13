fn main() {
    let rustc = std::env::var_os("RUSTC").unwrap_or_else(|| "rustc".into());
    let output = std::process::Command::new(&rustc)
        .args(["--print", "sysroot"])
        .output()
        .expect("rustc sysroot");
    assert!(output.status.success());
    let sysroot = String::from_utf8(output.stdout).expect("UTF-8 sysroot");
    println!("cargo:rustc-link-arg=-Wl,-rpath,{}/lib", sysroot.trim());
    println!("cargo:rustc-env=RUST_INTERP_SYSROOT={}", sysroot.trim());
    let version = std::process::Command::new(&rustc)
        .arg("-vV")
        .output()
        .expect("rustc version");
    assert!(version.status.success());
    let version = String::from_utf8(version.stdout).expect("UTF-8 rustc version");
    let commit = version
        .lines()
        .find_map(|line| line.strip_prefix("commit-hash: "))
        .filter(|hash| hash.len() == 40 && hash.bytes().all(|byte| byte.is_ascii_hexdigit()))
        .unwrap_or("unknown");
    println!("cargo:rustc-env=RUST_INTERP_RUSTC_COMMIT={commit}");
}
