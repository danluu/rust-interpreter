//! One implementation is used by the app, its build script, and optionally a
//! native proc macro. Qualification edits this function, not the assertions.
pub fn transform(input: u64, seed: u64) -> u64 {
    input * 3 + seed
}

// QUALIFICATION_ERROR_SLOT
