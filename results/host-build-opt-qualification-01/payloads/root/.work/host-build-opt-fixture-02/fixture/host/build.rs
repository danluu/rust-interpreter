fn main() {
    let opt = std::env::var("OPT_LEVEL").unwrap();
    let debug = std::env::var("DEBUG").unwrap();
    let package = std::env::var("CARGO_PKG_NAME").unwrap();
    let out = std::path::PathBuf::from(std::env::var_os("OUT_DIR").unwrap());
    std::fs::write(out.join("profile.json"), format!(
        r#"{{"package":"{package}","opt_level":"{opt}","debug":"{debug}"}}"#)).unwrap();
    println!("cargo:rustc-env=FIXTURE_BUILD_OPT_LEVEL={opt}");
    println!("cargo:rustc-env=FIXTURE_BUILD_DEBUG={debug}");
    println!("cargo:rerun-if-changed=build.rs");
    
}
