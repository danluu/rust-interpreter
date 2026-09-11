#![feature(core_intrinsics)]
#![allow(internal_features)]
use std::alloc::{Layout, alloc_zeroed, dealloc, realloc};

struct Guard<'a>(&'a mut u64);
#[repr(align(64))]
struct Aligned(u64);
const ALIGNED: Aligned = Aligned(17);
impl Drop for Guard<'_> {
    fn drop(&mut self) { *self.0 = self.0.wrapping_add(7); }
}

#[inline(never)]
fn make_box(value: u64) -> Box<u64> { Box::new(value.wrapping_add(11)) }

pub fn rust_interp_entry(seed: u64) -> u64 {
    let mut result = *make_box(seed);
    let local = Aligned(seed);
    let allocated = Box::new(Aligned(seed ^ 7));
    assert_eq!((&local as *const Aligned) as usize % 64, 0);
    assert_eq!((&*allocated as *const Aligned) as usize % 64, 0);
    assert_eq!((&ALIGNED as *const Aligned) as usize % 64, 0);
    result ^= local.0.wrapping_add(allocated.0).wrapping_add(ALIGNED.0);
    let mut dropped = seed;
    drop(Box::new(Guard(&mut dropped)));
    result ^= dropped;

    let mut values = Vec::new();
    for i in 0..seed % 29 { values.push(seed.wrapping_add(i * 17)); }
    values.reserve(11);
    values.extend(0..seed % 13);
    result ^= values.iter().fold(seed, |a, &b| a.wrapping_add(b));
    let chosen = std::hint::select_unpredictable(seed & 1 == 0, [seed; 17], [!seed; 17]);
    assert_eq!(chosen, if seed & 1 == 0 { [seed; 17] } else { [!seed; 17] });
    let chosen = std::hint::select_unpredictable(seed & 1 == 0, Box::new(seed), Box::new(!seed));
    result ^= *chosen;
    values.reverse();
    unsafe {
        let mut small = seed as u8;
        let mut other = Box::new(!small);
        std::intrinsics::typed_swap_nonoverlapping(&mut small, &mut *other);
        assert_eq!(*other, seed as u8);
        assert_eq!(small, !(seed as u8));
        let mut large = [seed; 17];
        let mut other = Box::new([!seed; 17]);
        std::intrinsics::typed_swap_nonoverlapping(&mut large, &mut *other);
        assert_eq!(large, [!seed; 17]);
        assert_eq!(*other, [seed; 17]);
        let mut aligned = Aligned(seed);
        let mut other = Box::new(Aligned(!seed));
        std::intrinsics::typed_swap_nonoverlapping(&mut aligned, &mut *other);
        assert_eq!(aligned.0, !seed);
        assert_eq!(other.0, seed);
        std::intrinsics::typed_swap_nonoverlapping(std::ptr::dangling_mut::<()>(), std::ptr::dangling_mut::<()>());
    }
    let mut captured = seed;
    let mut closure = |a: u8, b: u64| {
        captured = captured.wrapping_add(a as u64).wrapping_add(b);
        captured
    };
    result ^= closure(3, seed);
    let left = [seed, seed.rotate_left(7), !seed];
    let mut right = left;
    right[seed as usize % 3] ^= seed & 1;
    result = result.rotate_left(3) ^ (left == right) as u64;
    result = result.rotate_left(3) ^ (*Box::new(left) == right) as u64;
    while let Some(value) = values.pop() {
        result = result.rotate_left(5) ^ value;
    }
    values.shrink_to_fit();
    assert!(values.try_reserve(usize::MAX).is_err());
    let mut empty_values = Vec::<()>::new();
    for _ in 0..seed % 17 { empty_values.push(()); }
    result ^= empty_values.len() as u64;
    for byte in b"owned byte collection".to_vec() {
        result = result.wrapping_mul(3) ^ byte as u64;
    }

    unsafe {
        let layout = Layout::from_size_align(17, 64).unwrap();
        let initial = alloc_zeroed(layout);
        assert!(!initial.is_null());
        assert_eq!(initial as usize % 64, 0);
        for i in 0..17 { assert_eq!(*initial.add(i), 0); }
        *initial.add(16) = seed as u8;
        let grown = realloc(initial, layout, 95);
        assert!(!grown.is_null());
        assert_eq!(grown as usize % 64, 0);
        std::ptr::copy(grown, grown.add(3), 17);
        result ^= *grown.add(19) as u64;
        dealloc(grown, Layout::from_size_align(95, 64).unwrap());
    }
    result
}

fn main() {
    for arg in std::env::args().skip(1) {
        println!("{}", rust_interp_entry(arg.parse().unwrap()));
    }
}
