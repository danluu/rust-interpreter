//! Admission counts shared by lowering and its persistent/diagnostic records.
// Keep the existing serialized-byte and per-body limits independent: accepting
// more small concrete functions must not admit an unbounded cache or artifact.
pub(crate) const MAX_FUNCTIONS: usize = 32_768;
