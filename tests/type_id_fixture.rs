use std::any::{Any, TypeId};
use std::cell::Cell;
use std::hash::{Hash, Hasher};
use std::hint::black_box;
use std::rc::Rc;

const IDS: [TypeId; 8] = [
    TypeId::of::<u8>(), TypeId::of::<u16>(), TypeId::of::<u32>(),
    TypeId::of::<u64>(), TypeId::of::<i64>(), TypeId::of::<[u8; 7]>(),
    TypeId::of::<()>(), TypeId::of::<&'static [u8]>(),
];
static DATA: [u8; 4] = [3, 5, 11, 17];
static mut ID_SLOT: TypeId = TypeId::of::<u8>();
struct Mixed { id: TypeId, bytes: &'static [u8], function: fn(u64) -> u64 }
fn rotate(x: u64) -> u64 { x.rotate_left(19) }
const MIXED: Mixed = Mixed { id: TypeId::of::<&'static [u8]>(), bytes: &DATA, function: rotate };

struct Digest(u64);
impl Hasher for Digest {
    fn finish(&self) -> u64 { self.0 }
    fn write(&mut self, bytes: &[u8]) {
        for &byte in bytes { self.0 = self.0.wrapping_mul(0x100000001b3) ^ u64::from(byte); }
    }
}

pub fn type_id_entry(seed: u64) -> u64 {
    let ids = black_box(IDS);
    let mut digest = Digest(seed);
    for (i, id) in ids.iter().enumerate() {
        assert_eq!(*id, IDS[i]);
        for (j, other) in ids.iter().enumerate() {
            assert_eq!(id == other, i == j);
            assert_eq!(id.cmp(other).reverse(), other.cmp(id));
            // Only builtin types contribute numeric hashes/order to the output.
            // User-type hashes can differ when compiler crate identities differ.
            digest.write(&[if id < other { 1 } else if id > other { 2 } else { 0 }]);
        }
        id.hash(&mut digest);
    }
    let mixed = black_box(MIXED);
    assert_eq!(mixed.id, ids[7]);
    assert_eq!(mixed.bytes, &[3, 5, 11, 17]);
    assert_eq!((mixed.function)(seed), rotate(seed));
    unsafe {
        let pointer = &raw mut ID_SLOT;
        let original = pointer.read();
        assert_eq!(original, ids[0]);
        pointer.write(ids[3]);
        assert_eq!(pointer.read(), ids[3]);
        pointer.write(original);
    }
    digest.finish() ^ (mixed.function)(seed)
}

struct Payload { value: u64, dropped: Rc<Cell<u32>> }
impl Drop for Payload {
    fn drop(&mut self) { self.dropped.set(self.dropped.get() + 1); }
}

pub fn any_entry(seed: u64) -> u64 {
    let mut value = seed;
    let borrowed: &mut dyn Any = black_box(&mut value);
    assert!(borrowed.is::<u64>());
    assert!(!borrowed.is::<i64>());
    assert!(borrowed.downcast_ref::<u32>().is_none());
    *borrowed.downcast_mut::<u64>().unwrap() = seed.wrapping_add(13);
    assert_eq!(*borrowed.downcast_ref::<u64>().unwrap(), seed.wrapping_add(13));
    assert_eq!((&*borrowed).type_id(), TypeId::of::<u64>());

    let dropped = Rc::new(Cell::new(0));
    let erased: Box<dyn Any> = Box::new(Payload { value, dropped: dropped.clone() });
    assert_eq!((&*erased).type_id(), TypeId::of::<Payload>());
    let erased = match erased.downcast::<u64>() { Ok(_) => panic!("wrong downcast"), Err(x) => x };
    assert_eq!(dropped.get(), 0);
    let payload = match erased.downcast::<Payload>() { Ok(x) => x, Err(_) => panic!("lost payload") };
    assert_eq!(payload.value, seed.wrapping_add(13));
    let result = payload.value;
    drop(payload);
    assert_eq!(dropped.get(), 1);
    result ^ u64::from(dropped.get())
}

#[derive(Debug)]
struct ErrorPayload(u64);
impl std::fmt::Display for ErrorPayload {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result { f.write_str("payload") }
}
impl std::error::Error for ErrorPayload {}

pub fn io_error_entry(seed: u64) -> u64 {
    let error = std::io::Error::other(ErrorPayload(seed));
    assert_eq!(error.kind(), std::io::ErrorKind::Other);
    assert!(error.get_ref().unwrap().is::<ErrorPayload>());
    assert!(!error.get_ref().unwrap().is::<std::fmt::Error>());
    assert_eq!(error.get_ref().unwrap().downcast_ref::<ErrorPayload>().unwrap().0, seed);
    let error = match error.downcast::<std::fmt::Error>() {
        Ok(_) => panic!("wrong error downcast"), Err(error) => error,
    };
    assert_eq!(error.kind(), std::io::ErrorKind::Other);
    match error.downcast::<ErrorPayload>() {
        Ok(payload) => payload.0.rotate_left(7), Err(_) => panic!("lost error payload"),
    }
}

pub fn rust_interp_entry(seed: u64) -> u64 {
    type_id_entry(seed) ^ any_entry(seed) ^ io_error_entry(seed)
}
fn main() {
    for argument in std::env::args().skip(1) {
        println!("{}", rust_interp_entry(argument.parse().unwrap()));
    }
}
