// Include the entire upstream module and its ordinary Cargo invocation helper.
// This avoids compiling unrelated integration-test modules without changing any
// compiler-info-cache test or the Cargo commands those tests execute.
#[path = "testsuite/utils/ext.rs"]
mod ext;

mod prelude {
    pub use crate::ext::CargoProjectExt;
    pub use cargo_test_support::prelude::*;
}

#[path = "testsuite/rustc_info_cache.rs"]
mod rustc_info_cache;
