#![feature(allocator_api, coerce_unsized, unsize)]
use std::alloc::{AllocError, Allocator, Global, Layout};
use std::cell::Cell;
use std::marker::{PhantomData, Unsize};
use std::ops::CoerceUnsized;
use std::pin::Pin;
use std::ptr::NonNull;
use std::rc::Rc;
use std::sync::Arc;

trait First { fn first(&self) -> u64; }
trait Value { fn value(&self) -> u64; }
trait More: First + Value {}

#[repr(align(64))]
struct Counted<'a> { value: u64, drops: &'a Cell<u64> }
impl First for Counted<'_> { fn first(&self) -> u64 { self.value ^ 31 } }
impl Value for Counted<'_> { fn value(&self) -> u64 { self.value } }
impl More for Counted<'_> {}
impl Drop for Counted<'_> {
    fn drop(&mut self) { self.drops.set(self.drops.get() + 1); }
}

// Field offsets can change when the pointer becomes wide. Neither the marker
// nor the unrelated non-ZST fields may be mistaken for the coerced pointer.
struct Carrier<T: ?Sized> {
    stamp: u64,
    pointer: *const T,
    suffix: [u8; 3],
    marker: PhantomData<T>,
}
impl<T: ?Sized + Unsize<U>, U: ?Sized> CoerceUnsized<Carrier<U>> for Carrier<T> {}
impl<T: ?Sized> Copy for Carrier<T> {}
impl<T: ?Sized> Clone for Carrier<T> { fn clone(&self) -> Self { *self } }

#[derive(Clone)]
struct TaggedAllocator { tag: u64, deallocations: Rc<Cell<u64>> }
unsafe impl Allocator for TaggedAllocator {
    fn allocate(&self, layout: Layout) -> Result<NonNull<[u8]>, AllocError> {
        assert_eq!(self.tag, 0x1234_5678_9abc_def0);
        Global.allocate(layout)
    }
    unsafe fn deallocate(&self, pointer: NonNull<u8>, layout: Layout) {
        assert_eq!(self.tag, 0x1234_5678_9abc_def0);
        self.deallocations.set(self.deallocations.get() + 1);
        unsafe { Global.deallocate(pointer, layout); }
    }
}

pub fn rust_interp_entry(seed: u64) -> u64 {
    let drops = Cell::new(0);
    let mut result = seed;
    {
        let local = Counted { value: seed.rotate_left(11), drops: &drops };
        let thin = NonNull::from(&local);
        let more: NonNull<dyn More> = thin;
        let value: NonNull<dyn Value> = more;
        assert_eq!(value.as_ptr().cast::<()>() as usize % 64, 0);
        result ^= unsafe { value.as_ref().value() ^ more.as_ref().first() };

        let carrier = Carrier { stamp: !seed, pointer: &local as *const Counted<'_>,
            suffix: [3, 97, 251], marker: PhantomData };
        let carrier: Carrier<dyn More + '_> = carrier;
        let carrier: Carrier<dyn Value + '_> = carrier;
        assert_eq!(carrier.stamp, !seed);
        assert_eq!(carrier.suffix, [3, 97, 251]);
        result ^= unsafe { (&*carrier.pointer).value() };

        // The allocation has room for the wide value. Read the initialized
        // thin value through a raw pointer, then coerce into the same storage.
        let mut storage = std::mem::MaybeUninit::<Carrier<dyn Value + '_>>::uninit();
        let destination = storage.as_mut_ptr();
        let source = destination.cast::<Carrier<Counted<'_>>>();
        unsafe {
            source.write(Carrier { stamp: seed ^ 67, pointer: &local,
                suffix: [5, 101, 239], marker: PhantomData });
            *destination = *source;
            let aliased = destination.read();
            assert_eq!(aliased.stamp, seed ^ 67);
            assert_eq!(aliased.suffix, [5, 101, 239]);
            result ^= (&*aliased.pointer).value();
        }
    }
    assert_eq!(drops.get(), 1);

    for length in [0usize, 4] {
        let values = [seed, seed.rotate_left(1), !seed, seed.rotate_right(1)];
        let array = NonNull::from(&values);
        let slice: NonNull<[u64]> = array;
        assert_eq!(unsafe { slice.as_ref() }, values.as_slice());
        let empty: NonNull<[u64]> = NonNull::from(&[] as &[u64; 0]);
        assert!(unsafe { empty.as_ref() }.is_empty());
        let source = Carrier { stamp: seed ^ length as u64, pointer: &values as *const [u64; 4],
            suffix: [17, 23, 41], marker: PhantomData };
        let slice: Carrier<[u64]> = source;
        assert_eq!(slice.stamp, seed ^ length as u64);
        assert_eq!(slice.suffix, [17, 23, 41]);
        result ^= unsafe { (&*slice.pointer)[length % 4] };
    }
    let empty: Box<[u64]> = Box::default();
    assert!(empty.is_empty());
    drop(empty);

    {
        let concrete = Arc::new(Counted { value: seed.wrapping_add(7), drops: &drops });
        let weak = Arc::downgrade(&concrete);
        let weak: std::sync::Weak<dyn More + '_> = weak;
        let more: Arc<dyn More + '_> = concrete;
        let value: Arc<dyn Value + '_> = more.clone();
        let weak_value: std::sync::Weak<dyn Value + '_> = weak.clone();
        assert_eq!(Arc::strong_count(&value), 2);
        assert_eq!(Arc::as_ptr(&value).cast::<()>() as usize % 64, 0);
        assert_eq!(std::mem::size_of_val(&*value), 64);
        result ^= value.value() ^ weak_value.upgrade().unwrap().value();
        drop(value);
        drop(more);
        assert_eq!(drops.get(), 2);
        assert!(weak.upgrade().is_none());
        assert!(weak_value.upgrade().is_none());
    }
    {
        let concrete = Rc::new(Counted { value: seed.wrapping_add(13), drops: &drops });
        let weak = Rc::downgrade(&concrete);
        let weak: std::rc::Weak<dyn Value + '_> = weak;
        let more: Rc<dyn More + '_> = concrete;
        let value: Rc<dyn Value + '_> = more.clone();
        assert_eq!(Rc::strong_count(&value), 2);
        result = result.wrapping_add(value.value());
        drop(more);
        assert_eq!(drops.get(), 2);
        drop(value);
        assert_eq!(drops.get(), 3);
        assert!(weak.upgrade().is_none());
    }
    let array = Arc::new([seed, !seed, 19]);
    let weak = Arc::downgrade(&array);
    let weak: std::sync::Weak<[u64]> = weak;
    let slice: Arc<[u64]> = array;
    assert_eq!(slice.len(), 3);
    result ^= weak.upgrade().unwrap()[1];
    drop(slice);
    assert!(weak.upgrade().is_none());
    drop(weak);
    let array = Rc::new([seed, 29]);
    let slice: Rc<[u64]> = array;
    assert_eq!(slice.len(), 2);
    result ^= slice[0];
    drop(slice);

    let pinned: Pin<Box<dyn Value + '_>> = Box::pin(Counted { value: seed ^ 43, drops: &drops });
    result ^= pinned.as_ref().get_ref().value();
    drop(pinned);
    assert_eq!(drops.get(), 4);

    let deallocations = Rc::new(Cell::new(0));
    let allocator = TaggedAllocator { tag: 0x1234_5678_9abc_def0, deallocations: deallocations.clone() };
    let concrete = Box::new_in(Counted { value: seed ^ 53, drops: &drops }, allocator.clone());
    let more: Box<dyn More + '_, TaggedAllocator> = concrete;
    let value: Box<dyn Value + '_, TaggedAllocator> = more;
    result ^= value.value();
    drop(value);
    assert_eq!(drops.get(), 5);
    assert_eq!(deallocations.get(), 1);
    let array = Box::new_in([seed, 59, 61], allocator.clone());
    let slice: Box<[u64], TaggedAllocator> = array;
    assert_eq!(slice.len(), 3);
    assert_eq!(slice[1], 59);
    result = result.wrapping_add(slice[0]);
    drop(slice);
    assert_eq!(deallocations.get(), 2);
    drop(allocator);
    result
}

fn main() {
    for seed in std::env::args().skip(1) {
        println!("{}", rust_interp_entry(seed.parse().unwrap()));
    }
}
