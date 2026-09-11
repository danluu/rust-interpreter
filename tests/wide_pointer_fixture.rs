#![allow(ambiguous_wide_pointer_comparisons)]

use std::ptr;
#[cfg(with_arc)]
use std::sync::Arc;

#[inline(never)]
fn equal(a: *const [u8], b: *const [u8]) -> bool { a == b }
#[inline(never)]
fn unequal(a: *const [u8], b: *const [u8]) -> bool { a != b }
#[inline(never)]
fn mutable_equal(a: *mut [u8], b: *mut [u8]) -> bool { a == b }
#[inline(never)]
fn mutable_unequal(a: *mut [u8], b: *mut [u8]) -> bool { a != b }

#[repr(C)]
struct Tail<T: ?Sized> { prefix: u64, tail: T }
trait Value { fn value(&self) -> u64; }
impl Value for u64 { fn value(&self) -> u64 { *self } }

pub fn rust_interp_entry(seed: u64) -> u64 {
    let mut bytes = [seed as u8; 32];
    let base = bytes.as_mut_ptr();
    let mut result = seed;
    // Only compare these raw values; never dereference null or overlong slices.
    // Full-width metadata must survive, including a difference only at bit 63.
    let lengths = [0usize, 1, 7, 16, 1usize << 32, 1usize << 63, usize::MAX, seed as usize];
    for left in 0..lengths.len() {
        for right in 0..lengths.len() {
            for shift in [0usize, 1, 16] {
                let p = ptr::slice_from_raw_parts(base, lengths[left]);
                let q = ptr::slice_from_raw_parts(base.wrapping_add(shift), lengths[right]);
                let expected = shift == 0 && lengths[left] == lengths[right];
                assert_eq!(equal(p, q), expected);
                assert_eq!(unequal(p, q), !expected);
                assert_eq!(ptr::eq(p, q), expected);
                assert_eq!(ptr::addr_eq(p, q), shift == 0);
                let p_mut = ptr::slice_from_raw_parts_mut(base, lengths[left]);
                let q_mut = ptr::slice_from_raw_parts_mut(base.wrapping_add(shift), lengths[right]);
                assert_eq!(mutable_equal(p_mut, q_mut), expected);
                assert_eq!(mutable_unequal(p_mut, q_mut), !expected);
                let null_p = ptr::slice_from_raw_parts(ptr::null::<u8>(), lengths[left]);
                let null_q = ptr::slice_from_raw_parts(ptr::null::<u8>(), lengths[right]);
                assert_eq!(equal(null_p, null_q), lengths[left] == lengths[right]);
                assert_eq!(unequal(null_p, null_q), lengths[left] != lengths[right]);
                assert!(!equal(p, null_q));
                result = result.rotate_left(1).wrapping_add(expected as u64);
            }
        }
    }
    let text = "metadata matters";
    assert!(ptr::eq(text as *const str, text as *const str));
    assert!(!ptr::eq(text as *const str, &text[..3] as *const str));
    assert!(ptr::addr_eq(text as *const str, &text[..3] as *const str));
    let first = Tail { prefix: seed, tail: [1u8; 8] };
    let second = Tail { prefix: seed, tail: [1u8; 8] };
    let a: *const Tail<[u8]> = &first;
    let b: *const Tail<[u8]> = &second;
    assert!(ptr::eq(a, a));
    assert!(!ptr::eq(a, b));
    let fields = (seed, [a, b, a]);
    assert!(ptr::eq(fields.1[0], fields.1[2]));
    assert!(!ptr::eq(fields.1[0], fields.1[1]));

    let value = seed;
    let other = !seed;
    let object: *const dyn Value = &value;
    let alias = object;
    let different: *const dyn Value = &other;
    assert!(ptr::eq(object, alias));
    assert!(!ptr::eq(object, different));
    result ^= unsafe { (&*object).value() };

    // Installed std omits non-generic Arc allocation MIR at level 0. Exercise
    // this section with the metadata sysroot; raw-pointer cases use both.
    #[cfg(with_arc)]
    {
    let shared: Arc<str> = Arc::from(text);
    let clone = shared.clone();
    let same_value: Arc<str> = Arc::from(text);
    let shorter: Arc<str> = Arc::from(&text[..3]);
    let other_value: Arc<str> = Arc::from("metadata differs");
    assert!(shared == clone);
    assert!(!(shared != clone));
    assert!(shared == same_value);
    assert!(!(shared != same_value));
    assert!(shared != shorter);
    assert!(!(shared == shorter));
    assert!(shared != other_value);
    assert!(Arc::ptr_eq(&shared, &clone));
    assert!(!Arc::ptr_eq(&shared, &same_value));
    let shared_bytes: Arc<[u8]> = Arc::from(bytes.as_slice());
    let clone_bytes = shared_bytes.clone();
    let same_bytes: Arc<[u8]> = Arc::from(bytes.as_slice());
    assert!(shared_bytes == clone_bytes && shared_bytes == same_bytes);
    }
    result
}

fn main() {
    for arg in std::env::args().skip(1) {
        println!("{}", rust_interp_entry(arg.parse().unwrap()));
    }
}
