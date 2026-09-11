#![allow(dead_code)]

#[derive(Debug)]
#[repr(align(64))]
struct LargeError([u64; 32]);

#[test] fn unit_ok() {}
#[test] fn tagged_ok() -> Result<(), u64> { Ok(()) }
#[test] fn tagged_err() -> Result<(), u64> { Err(19) }
#[test] fn niche_ok() -> Result<(), std::num::NonZeroU64> { Ok(()) }
#[test] fn niche_err() -> Result<(), std::num::NonZeroU64> {
    Err(std::num::NonZeroU64::new(31).unwrap())
}
#[test] fn bool_ok() -> Result<(), bool> { Ok(()) }
#[test] fn bool_err() -> Result<(), bool> { Err(false) }
#[test] fn empty_error() -> Result<(), std::convert::Infallible> { Ok(()) }
#[test] fn large_ok() -> Result<(), LargeError> { Ok(()) }
#[test] fn large_err() -> Result<(), LargeError> { Err(LargeError([23; 32])) }
#[test] fn string_ok() -> Result<(), String> { Ok(()) }
#[test] fn string_err() -> Result<(), String> { Err("owned error".into()) }

type Alias = Result<(), &'static str>;
#[test] fn alias_ok() -> Alias { Ok(()) }
#[test] fn alias_err() -> Alias { Err("borrowed error") }

// Error would occur only if a batch erroneously continued after an Err result.
#[test] fn later_panic() { panic!("RESULT_BATCH_CONTINUED"); }

fn scalar_success() -> Result<u64, ()> { Ok(7) }
fn argument_result(_value: u64) -> Result<(), ()> { Ok(()) }
mod lookalike { pub enum Result<T, E> { Ok(T), Err(E) } }
fn fake_result() -> lookalike::Result<(), ()> { lookalike::Result::Ok(()) }
