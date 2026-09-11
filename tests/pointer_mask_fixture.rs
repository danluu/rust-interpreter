#![feature(ptr_mask, ptr_metadata)]

#[repr(align(64))]
struct Aligned([u64; 8]);
trait Value { fn value(&self) -> u64; }
impl Value for Aligned { fn value(&self) -> u64 { self.0[3] } }

pub fn rust_interp_entry(seed: u64) -> u64 {
    let stack = Aligned([seed; 8]);
    let original = &stack as *const Aligned;
    let mut result = 0u64;
    for tag in 0..64 {
        let tagged = original.map_addr(|address| address | tag);
        let restored = tagged.mask(!63);
        assert_eq!(restored, original);
        let value = unsafe { (*restored).0[tag % 8] };
        assert_eq!(value, seed);
        result = result.rotate_left(3).wrapping_add(value ^ tag as u64);
    }
    let mut heap = Box::new(Aligned([!seed; 8]));
    let original = &mut *heap as *mut Aligned;
    for tag in 0..64 {
        let tagged = original.map_addr(|address| address | tag);
        let restored = tagged.mask(!63);
        assert_eq!(restored, original);
        unsafe { (*restored).0[tag % 8] = seed.wrapping_add(tag as u64); }
    }
    for (index, value) in heap.0.iter().enumerate() {
        assert_eq!(*value, seed.wrapping_add(56 + index as u64));
    }
    result ^= heap.0.iter().fold(0, |a, b| a ^ b);

    let slice: *const [u64] = &stack.0;
    let object: *const dyn Value = &stack;
    for tag in 0..8 {
        let tagged = slice.map_addr(|address| address | tag);
        let restored = tagged.mask(!7);
        assert_eq!(restored.addr(), slice.addr());
        assert_eq!(std::ptr::metadata(restored), 8);
        result ^= unsafe { (&*restored)[tag] };

        let tagged = object.map_addr(|address| address | tag);
        let restored = tagged.mask(!7);
        assert_eq!(restored.addr(), object.addr());
        assert_eq!(std::ptr::metadata(restored), std::ptr::metadata(object));
        result ^= unsafe { (&*restored).value() };
    }
    // Null and empty-data results are pointer values only; never dereference.
    let masked = slice.mask(0);
    assert_eq!(masked.addr(), 0);
    assert_eq!(std::ptr::metadata(masked), 8);
    let masked = object.mask(0);
    assert_eq!(masked.addr(), 0);
    assert_eq!(std::ptr::metadata(masked), std::ptr::metadata(object));
    assert_eq!(original.mask(usize::MAX), original);
    assert!(std::ptr::null::<u64>().mask(!7).is_null());
    result
}

fn main() {
    for arg in std::env::args().skip(1) {
        println!("{}", rust_interp_entry(arg.parse().unwrap()));
    }
}
