// Future diagnostic fixture, uncompiled/unrun. Comments describe proposed gate
// categories only; ordinary rustc remains authoritative for program behavior.
#![allow(dead_code)]

struct Counter { value: u32 }
trait ReadCounter { fn read(&self) -> u32; }
impl Counter {
    #[inline] // Stock attribute lowering must still run; body has no attributes.
    fn add(&mut self, amount: u32) { self.value += amount; }
    fn read_inherent(&self) -> u32 { self.value }
    fn twice(&self) -> u32 { self.read_inherent() + self.read_inherent() }
}
impl ReadCounter for Counter {
    fn read(&self) -> u32 { self.value }
}
trait DefaultBody {
    fn read(&self) -> u32;
    fn double(&self) -> u32 { self.read() + self.read() }
}
fn local_value(x: u32) -> u32 { x + 3 }
fn local_call(x: u32) -> u32 { local_value(x) }
fn external_call(x: i64) -> i64 { std::cmp::max(x, 4) } // Pending actual legacy-attribute proof.
fn via_trait<T: ReadCounter>(x: &T) -> u32 { x.read() } // Generic signature remains stock.
fn conditional(x: &Counter, yes: bool) -> u32 { if yes { x.value } else { 0 } }
fn nested_definition() -> u32 { fn inner() -> u32 { 1 } inner() } // Fallback.
fn closure() -> u32 { let f = || 1; f() } // Fallback: nested definition.
fn body_type(x: &u32) -> u32 { let y: &u32 = x; *y } // Fallback: body type/lifetime path.
fn macro_body() -> u32 { assert!(true); 1 } // Fallback: expansion/context/desugaring.

fn main() {
    let mut counter = Counter { value: 4 };
    counter.add(local_call(2));
    assert_eq!(counter.twice(), 18);
    assert_eq!(via_trait(&counter), 9);
    assert_eq!(conditional(&counter, false), 0);
    assert_eq!(external_call(9), 9);
}
