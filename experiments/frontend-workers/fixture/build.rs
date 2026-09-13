fn main() {
    let out = std::path::PathBuf::from(std::env::var_os("OUT_DIR").unwrap());
    std::fs::write(out.join("value.rs"),
        format!("const HOST_VALUE: u64 = {};", worker_shared::value())).unwrap();
    println!("cargo::rerun-if-changed=build.rs");
}
