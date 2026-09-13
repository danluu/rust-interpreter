#![allow(dead_code, unused_imports)]
extern crate bridge_fixture;
use bridge_fixture::{explode, fail, warn};

warn!(still_runs_before_error);

#[cfg(type_error)]
fn uncalled_type() { let _: u64 = "wrong"; }
#[cfg(borrow_error)]
fn uncalled_borrow() { let value = String::new(); drop(value); drop(value); }
#[cfg(const_error)]
const UNCALLED: usize = { panic!("bridge fixture const error") };
#[cfg(macro_error)]
fail!(error_site);
#[cfg(macro_panic)]
explode!(panic_site);

fn main() {}
