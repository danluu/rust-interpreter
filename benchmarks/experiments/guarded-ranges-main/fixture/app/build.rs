fn main() {
    let output = std::path::PathBuf::from(std::env::var_os("OUT_DIR").unwrap());
    std::fs::write(output.join("generated.rs"), format!(
        "pub const HOST_VALUE: u64 = {};\n", host_mir_shared::shared_value(1),
    )).unwrap();
    println!("cargo::rerun-if-changed=build.rs");
}
