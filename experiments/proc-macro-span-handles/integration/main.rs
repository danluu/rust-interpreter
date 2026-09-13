#![allow(dead_code)]
extern crate bridge_fixture;
use bridge_fixture::{inner, nested, probe, warn};

// POSITION_EDIT: insert two empty lines immediately after this comment.
warn!(warning_site);
const FIRST: u64 = probe!(first { [alpha + 3, (beta, "literal")] });
const SECOND: u64 = probe!(second { [gamma + 4, (delta, b"bytes")] });
const NESTED: u64 = nested!(inner!());

pub fn rust_interp_entry() -> u64 { FIRST + SECOND + NESTED }
fn main() { println!("{}", rust_interp_entry()); }
