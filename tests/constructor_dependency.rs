//! Kept in a separate crate: external constructors have CTFE MIR, not optimized MIR.
pub struct Wrapped<T>(pub T);
pub enum Choice<T> { Some(T), Other(u16) }

