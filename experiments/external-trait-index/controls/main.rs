#![feature(trait_alias)]
#![allow(non_upper_case_globals)]

extern crate external;

#[cfg(not(select_right))]
use external::reexport::nested::Selected;
#[cfg(select_right)]
use external::right::Select as Selected;
#[cfg(ambiguous)]
use external::right::Select as AlsoSelected;
#[cfg(unused_import)]
use external::Unused as UnusedSelected;

fn select(value: &external::Foreign) -> u32 { value.selected() }
fn alias<T: external::Alias>(value: &T) -> u32 {
    // Trait aliases must keep the resolver's conservative candidate behavior.
    value.absent_from_right()
}
fn associated_type(value: <external::Foreign as external::left::Select>::Item) -> u32 {
    // The associated type and constant intentionally have the same symbol.
    value + <external::Foreign as external::left::Select>::Item
}
fn local(value: &external::Foreign) -> u32 {
    external::make_local_trait!();
    value.locally_defined()
}

#[cfg(missing_method)]
fn uncalled_missing(value: &external::Foreign) -> u32 { value.no_such_method() }
#[cfg(type_error)]
fn uncalled_type_error(value: &external::Foreign) -> String { value.selected() }
#[cfg(borrow_error)]
fn uncalled_borrow_error() {
    let text = String::from("current checking remains active");
    let _moved = text;
    drop(text);
}
#[cfg(const_error)]
const UNCALLED_CONST: u32 = 1 / 0;

fn main() {
    let value = external::Foreign(3);
    let mut total = 0;
    for _ in 0..32 { total += select(&value); }
    assert_eq!(alias(&value), 7);
    assert_eq!(associated_type(9), 40);
    assert_eq!(local(&value), 8);
    println!("{total}");
}
