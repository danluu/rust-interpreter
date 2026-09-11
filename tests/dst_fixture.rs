use std::cell::Cell;

#[repr(C)]
struct Header<T: ?Sized> { tag: u8, tail: T }
#[repr(C, align(32))]
struct Outer<T: ?Sized> { tag: [u8; 3], tail: T }
#[repr(C, packed(2))]
struct Packed<T: ?Sized> { tag: u8, tail: std::mem::ManuallyDrop<T> }

trait Value { fn value(&self) -> u64; }
trait First { fn first(&self) -> u64; }
trait More: First + Value { fn more(&self) -> u64; }
struct Small(u64);
#[repr(align(64))]
struct Wide(u64);
impl Value for Small { fn value(&self) -> u64 { self.0 } }
impl First for Small { fn first(&self) -> u64 { self.0 ^ 31 } }
impl More for Small { fn more(&self) -> u64 { self.0.rotate_left(3) } }
impl Value for Wide { fn value(&self) -> u64 { self.0 } }
impl First for Wide { fn first(&self) -> u64 { self.0 ^ 97 } }
impl More for Wide { fn more(&self) -> u64 { self.0.rotate_left(7) } }
#[repr(align(64))]
struct Counted<'a> { value: u64, drops: &'a Cell<u64> }
impl Value for Counted<'_> { fn value(&self) -> u64 { self.value } }
impl Drop for Counted<'_> {
    fn drop(&mut self) { self.drops.set(self.drops.get() + 1); }
}

#[inline(never)]
fn check_layout<T: ?Sized, U>(erased: &T, sized: &U) {
    assert_eq!(std::mem::size_of_val(erased), std::mem::size_of_val(sized));
    assert_eq!(std::mem::align_of_val(erased), std::mem::align_of_val(sized));
}

pub fn rust_interp_entry(seed: u64) -> u64 {
    let array = Header { tag: 7, tail: [seed, !seed, seed.rotate_left(13)] };
    let slice: &Header<[u64]> = &array;
    check_layout(slice, &array);
    assert_eq!(slice.tail.len(), 3);
    let empty = Header { tag: 5, tail: [0u64; 0] };
    let slice_empty: &Header<[u64]> = &empty;
    check_layout(slice_empty, &empty);
    assert_eq!(slice_empty.tail.len(), 0);

    let concrete = Outer { tag: [1, 2, 3], tail: Header { tag: 9, tail: Wide(seed) } };
    let object: &Outer<Header<dyn More>> = &concrete;
    check_layout(object, &concrete);
    let base: &Outer<Header<dyn Value>> = object;
    check_layout(base, &concrete);
    assert_eq!(object.tail.tag, 9);
    assert_eq!(base.tail.tail.value(), seed);
    assert_eq!(object.tail.tail.more(), seed.rotate_left(7));
    assert_eq!(object.tail.tail.first(), seed ^ 97);
    let expected = std::ptr::addr_of!(concrete.tail.tail) as usize
        - std::ptr::addr_of!(concrete) as usize;
    let actual = std::ptr::addr_of!(base.tail.tail) as *const () as usize
        - base as *const _ as *const () as usize;
    assert_eq!(actual, expected);
    assert_eq!(actual % 64, 0);

    let small = Header { tag: 11, tail: Small(!seed) };
    let small_dyn: &Header<dyn Value> = &small;
    check_layout(small_dyn, &small);
    assert_eq!(small_dyn.tail.value(), !seed);
    let nested_small = Outer { tag: [3, 4, 5], tail: small };
    let nested_small_dyn: &Outer<Header<dyn Value>> = &nested_small;
    check_layout(nested_small_dyn, &nested_small);
    assert_eq!(nested_small_dyn.tail.tail.value(), !seed);

    let packed = Packed { tag: 13, tail: std::mem::ManuallyDrop::new([seed, !seed, 17]) };
    let packed_slice: &Packed<[u64]> = &packed;
    check_layout(packed_slice, &packed);
    let tail = std::ptr::addr_of!(packed_slice.tail) as *const u64;
    assert_eq!(unsafe { tail.read_unaligned() }, seed);
    assert_eq!(tail as usize - packed_slice as *const _ as *const () as usize, 2);

    let packed = Packed { tag: 19, tail: std::mem::ManuallyDrop::new(Small(seed)) };
    let packed_object: &Packed<dyn Value> = &packed;
    check_layout(packed_object, &packed);
    // Only inspect the raw field address: taking a reference to its unaligned
    // concrete value would violate Rust's reference-alignment requirements.
    let tail = std::ptr::addr_of!(packed_object.tail) as *const () as usize;
    assert_eq!(tail - packed_object as *const _ as *const () as usize, 2);

    let drops = Cell::new(0);
    let owned: Box<Outer<Header<dyn Value + '_>>> = Box::new(Outer {
        tag: [7, 8, 9], tail: Header { tag: 17, tail: Counted { value: seed, drops: &drops } },
    });
    assert_eq!(owned.tail.tail.value(), seed);
    drop(owned);
    assert_eq!(drops.get(), 1);

    let path = std::path::Path::new("alpha/β");
    assert_eq!(std::mem::size_of_val(path), "alpha/β".len());
    assert_eq!(std::mem::align_of_val(path), 1);
    slice.tail[2] ^ actual as u64 ^ drops.get()
}

fn main() {
    for arg in std::env::args().skip(1) {
        println!("{}", rust_interp_entry(arg.parse().unwrap()));
    }
}
