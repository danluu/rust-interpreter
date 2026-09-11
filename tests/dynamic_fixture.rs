#![feature(ptr_metadata)]
use std::cell::Cell;

struct Payload(u128, u16);
trait Value {
    fn value(&self, seed: u64) -> u64;
    fn bump(&mut self, delta: u64);
    fn payload(&self, input: Payload) -> Payload {
        Payload(input.0.wrapping_add(self.value(input.1 as u64) as u128), input.1 ^ 17)
    }
}
trait First { fn first(&self) -> u64; }
trait Second { fn second(&self) -> u64; }
trait Combined: First + Second + Value {}

struct Small(u64);
#[repr(align(64))]
struct Large([u64; 9]);
impl Value for Small {
    fn value(&self, seed: u64) -> u64 { self.0.wrapping_add(seed) }
    fn bump(&mut self, delta: u64) { self.0 = self.0.wrapping_add(delta); }
}
impl First for Small { fn first(&self) -> u64 { self.0 ^ 3 } }
impl Second for Small { fn second(&self) -> u64 { self.0 ^ 7 } }
impl Combined for Small {}
impl Value for Large {
    fn value(&self, seed: u64) -> u64 { self.0.iter().fold(seed, |a, b| a.wrapping_add(*b)) }
    fn bump(&mut self, delta: u64) { self.0[3] = self.0[3].wrapping_add(delta); }
}
impl First for Large { fn first(&self) -> u64 { self.0[0] ^ 5 } }
impl Second for Large { fn second(&self) -> u64 { self.0[0] ^ 11 } }
impl Combined for Large {}

struct Counted<'a> { value: u64, counter: &'a Cell<u64> }
impl Value for Counted<'_> {
    fn value(&self, seed: u64) -> u64 { self.value ^ seed }
    fn bump(&mut self, delta: u64) { self.value = self.value.wrapping_add(delta); }
}
impl Drop for Counted<'_> {
    fn drop(&mut self) { self.counter.set(self.counter.get().wrapping_add(self.value)); }
}

const CONSTANT: &dyn Value = &Small(19);
struct Link { value: u64, next: &'static Link }
static FIRST_LINK: Link = Link { value: 37, next: &SECOND_LINK };
static SECOND_LINK: Link = Link { value: 41, next: &FIRST_LINK };
static ALIGNED: Large = Large([13; 9]);
#[inline(never)]
fn choose<'a>(which: bool, a: &'a dyn Value, b: &'a dyn Value) -> &'a dyn Value {
    if which { a } else { b }
}
#[inline(never)]
fn read(value: &dyn Value) -> u64 { value.value(31) }

pub fn rust_interp_entry(seed: u64) -> u64 {
    let small = Small(seed);
    let large = Large([seed.rotate_left(7); 9]);
    let mut result = choose(seed & 1 == 0, &small, &large).value(seed);
    // Thin pointer aggregates still carry a unit metadata operand in MIR.
    let pointer = std::ptr::from_raw_parts::<Small>(&small as *const Small, ());
    assert!(std::ptr::eq(pointer, &small));
    result ^= unsafe { (*pointer).value(29) };
    let mut slot = seed;
    let pointer = std::ptr::from_raw_parts_mut::<u64>(&mut slot as *mut u64, ());
    unsafe { *pointer = (*pointer).wrapping_add(23); }
    result ^= slot;
    let slice = [seed, !seed, seed.rotate_left(5)];
    let pointer = std::ptr::from_raw_parts::<[u64]>(slice.as_ptr(), slice.len());
    result ^= unsafe { (&*pointer)[2] };
    let mut slice = [seed, !seed];
    let pointer = std::ptr::from_raw_parts_mut::<[u64]>(slice.as_mut_ptr(), slice.len());
    unsafe { (&mut *pointer)[1] ^= 31; }
    result ^= slice[1];
    let original: &dyn Value = &small;
    let pointer = std::ptr::from_raw_parts::<dyn Value>(
        &small as *const Small, std::ptr::metadata(original),
    );
    result ^= unsafe { (&*pointer).value(43) };
    result ^= CONSTANT.value(seed);
    result ^= FIRST_LINK.next.value ^ SECOND_LINK.next.value ^ ALIGNED.0[seed as usize % 9];
    assert!(std::ptr::eq(FIRST_LINK.next.next, &FIRST_LINK));
    assert_eq!((&ALIGNED as *const Large as usize) % 64, 0);
    let callback: fn(&dyn Value) -> u64 = std::hint::black_box(read);
    result ^= callback(&small);
    // Closure vtable methods can be Item instances without a fn_sig query.
    // Exercise both a borrowed capture and a mutable, heap-owned capture.
    let captured = |value: u64| value.wrapping_add(seed.rotate_left(11));
    let callable: &dyn Fn(u64) -> u64 = &captured;
    result ^= callable(seed);
    let mut state = seed;
    let mut mutable: Box<dyn FnMut(u64) -> u64> = Box::new(move |value| {
        state = state.wrapping_add(value);
        state.rotate_right(3)
    });
    result ^= mutable(17);
    result ^= mutable(seed);
    drop(mutable);

    for value in [&small as &dyn Combined, &large as &dyn Combined] {
        let first: &dyn First = value;
        let second: &dyn Second = value;
        let base: &dyn Value = value;
        result = result.rotate_left(3) ^ first.first() ^ second.second();
        let output = base.payload(Payload((seed as u128) << 80, seed as u16));
        result ^= output.0 as u64 ^ (output.0 >> 64) as u64 ^ output.1 as u64;
    }
    let send: &(dyn Value + Send) = &small;
    let plain: &dyn Value = send;
    result ^= plain.value(23);

    let mut boxed: Box<dyn Value> = if seed & 1 == 0 {
        Box::new(Small(seed))
    } else {
        Box::new(Large([seed; 9]))
    };
    let (size, align) = if seed & 1 == 0 {
        (std::mem::size_of::<Small>(), std::mem::align_of::<Small>())
    } else {
        (std::mem::size_of::<Large>(), std::mem::align_of::<Large>())
    };
    assert_eq!(std::mem::size_of_val(&*boxed), size);
    assert_eq!(std::mem::align_of_val(&*boxed), align);
    boxed.bump(13);
    result ^= boxed.value(seed);
    drop(boxed); // Null vtable drop entries still deallocate the Box.

    let counter = Cell::new(seed);
    let mut counted: Box<dyn Value + '_> = Box::new(Counted { value: 17, counter: &counter });
    counted.bump(5);
    drop(counted);
    assert_eq!(counter.get(), seed.wrapping_add(22));
    let slice: Box<[Counted<'_>]> = (1..=3).map(|value| Counted { value, counter: &counter })
        .collect::<Vec<_>>().into_boxed_slice();
    drop(slice);
    assert_eq!(counter.get(), seed.wrapping_add(28));
    result ^= counter.get();

    let text = format!("{seed}:{:016x}:{}", seed.rotate_left(17), CONSTANT.value(seed));
    for byte in text.bytes() { result = result.rotate_left(5).wrapping_add(byte as u64); }
    result
}

fn main() {
    for arg in std::env::args().skip(1) {
        println!("{}", rust_interp_entry(arg.parse().unwrap()));
    }
}
