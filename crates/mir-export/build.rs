fn main() {
    let rustc = std::env::var_os("RUSTC").unwrap_or_else(|| "rustc".into());
    let output = std::process::Command::new(rustc)
        .args(["--print", "sysroot"])
        .output()
        .expect("rustc sysroot");
    assert!(output.status.success());
    let sysroot = String::from_utf8(output.stdout).expect("UTF-8 sysroot");
    println!("cargo:rustc-link-arg=-Wl,-rpath,{}/lib", sysroot.trim());
    println!("cargo:rustc-env=RUST_INTERP_SYSROOT={}", sysroot.trim());
}
