#![feature(allocator_api)]
use std::alloc::{Allocator, Layout, System};

unsafe extern "C" {
    fn malloc(size: usize) -> *mut u8;
    fn calloc(count: usize, size: usize) -> *mut u8;
    fn free(pointer: *mut u8);
    fn realloc(pointer: *mut u8, size: usize) -> *mut u8;
    fn posix_memalign(output: *mut *mut u8, align: usize, size: usize) -> i32;
    fn __error() -> *mut i32;
}

pub fn rust_interp_entry(seed: u64) -> u64 {
    let size = (seed % 127 + 1) as usize;
    let impossible = std::hint::black_box(usize::MAX);
    let mut result = seed;
    unsafe {
        let error = __error();
        assert_eq!(error, __error());
        *error = 7;
        let pointer = calloc(size, 1);
        assert!(!pointer.is_null());
        assert_eq!(pointer as usize % 16, 0);
        assert_eq!(*error, 7);
        for i in 0..size {
            assert_eq!(*pointer.add(i), 0);
            *pointer.add(i) = (seed as u8).wrapping_add(i as u8);
        }
        let grown = realloc(pointer, size + 49);
        assert!(!grown.is_null());
        assert_eq!(grown as usize % 16, 0);
        for i in 0..size {
            assert_eq!(*grown.add(i), (seed as u8).wrapping_add(i as u8));
            result = result.rotate_left(5) ^ *grown.add(i) as u64;
        }
        *error = 7;
        // Keep failure results observable: the native optimizer may otherwise
        // elide an allocation whose only use is a null comparison.
        assert!(std::hint::black_box(realloc(grown, impossible)).is_null());
        assert_eq!(*error, 12);
        for i in 0..size { assert_eq!(*grown.add(i), (seed as u8).wrapping_add(i as u8)); }
        let zero = realloc(grown, 0);
        assert!(!zero.is_null());
        free(zero);

        for pointer in [malloc(0), calloc(0, impossible), realloc(std::ptr::null_mut(), 0)] {
            assert!(!pointer.is_null());
            assert_eq!(pointer as usize % 16, 0);
            free(pointer);
        }
        *error = 7;
        free(std::ptr::null_mut());
        assert_eq!(*error, 7);
        assert!(std::hint::black_box(malloc(impossible)).is_null());
        assert_eq!(*error, 12);
        *error = 7;
        assert!(std::hint::black_box(calloc(impossible, 2)).is_null());
        assert_eq!(*error, 12);

        for alignment in [8, 16, 64, 4096] {
            let mut pointer = std::ptr::null_mut();
            *error = 7;
            assert_eq!(posix_memalign(&mut pointer, alignment, size), 0);
            assert!(!pointer.is_null());
            assert_eq!(pointer as usize % alignment, 0);
            assert_eq!(*error, 7);
            *pointer.add(size - 1) = seed as u8;
            result = result.rotate_left(3) ^ *pointer.add(size - 1) as u64;
            free(pointer);
        }
        for alignment in [0, 3, 4, 12] {
            let mut pointer = 0x1234usize as *mut u8;
            *error = 7;
            assert_eq!(posix_memalign(&mut pointer, alignment, size), 22);
            assert_eq!(pointer as usize, 0x1234);
            assert_eq!(*error, 7);
        }
        let mut pointer = 0x1234usize as *mut u8;
        assert_eq!(posix_memalign(&mut pointer, 16, impossible), 12);
        assert_eq!(pointer as usize, 0x1234);
        assert_eq!(*error, 7);
        assert_eq!(posix_memalign(&mut pointer, 64, 0), 0);
        assert!(!pointer.is_null());
        assert_eq!(pointer as usize % 64, 0);
        free(pointer);
    }
    result
}

pub fn system_entry(seed: u64) -> u64 {
    let mut values = Vec::<u64, System>::new_in(System);
    for i in 0..seed % 79 + 1 { values.push(seed.wrapping_add(i * 17)); }
    values.reserve(49);
    values.reverse();
    values.shrink_to_fit();
    let mut result = values.iter().fold(seed, |a, b| a.rotate_left(7) ^ b);
    assert!(values.try_reserve(usize::MAX).is_err());
    unsafe {
        let small = Layout::from_size_align(19, 64).unwrap();
        let large = Layout::from_size_align(93, 128).unwrap();
        let shrunk = Layout::from_size_align(17, 64).unwrap();
        let initial = System.allocate_zeroed(small).unwrap();
        assert_eq!(initial.as_ptr() as *mut u8 as usize % 64, 0);
        for i in 0..19 {
            assert_eq!(*initial.as_ptr().cast::<u8>().add(i), 0);
            *initial.as_ptr().cast::<u8>().add(i) = (seed as u8).wrapping_add(i as u8);
        }
        let grown = System.grow_zeroed(initial.cast(), small, large).unwrap();
        assert_eq!(grown.as_ptr() as *mut u8 as usize % 128, 0);
        for i in 0..19 { assert_eq!(*grown.as_ptr().cast::<u8>().add(i), (seed as u8).wrapping_add(i as u8)); }
        for i in 19..93 { assert_eq!(*grown.as_ptr().cast::<u8>().add(i), 0); }
        let smaller = System.shrink(grown.cast(), large, shrunk).unwrap();
        assert_eq!(smaller.as_ptr() as *mut u8 as usize % 64, 0);
        for i in 0..17 { result = result.rotate_left(3) ^ *smaller.as_ptr().cast::<u8>().add(i) as u64; }
        System.deallocate(smaller.cast(), shrunk);
        let zero_layout = Layout::from_size_align(0, 64).unwrap();
        let zero = System.allocate(zero_layout).unwrap();
        assert_eq!(zero.len(), 0);
        System.deallocate(zero.cast(), zero_layout);
    }
    result
}

fn main() {
    let mut args = std::env::args().skip(1);
    let name = args.next().unwrap();
    for seed in args {
        let seed = seed.parse().unwrap();
        println!("{}", if name == "raw" { rust_interp_entry(seed) } else { system_entry(seed) });
    }
}
