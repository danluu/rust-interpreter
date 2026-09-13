#[cfg(test)]
mod tests {
    use std::cell::Cell;
    use std::hint::black_box;

    struct Counted<'a>(&'a Cell<u64>, u64);
    impl Drop for Counted<'_> {
        fn drop(&mut self) { self.0.set(self.0.get() + self.1); }
    }

    #[test]
    fn owned_capture_and_drop_once() {
        let dropped = Cell::new(0);
        let token = Counted(&dropped, 1);
        let text = String::from("boxed callback");
        let values = vec![3u64, 5, 11];
        let callback: Box<dyn FnOnce(u64) -> (String, u64) + '_> = Box::new(move |extra| {
            drop(token);
            (text, values.into_iter().sum::<u64>() + extra)
        });
        let (text, total) = black_box(callback)(23);
        assert_eq!(text, "boxed callback");
        assert_eq!(total, 42);
        assert_eq!(dropped.get(), 1);
    }

    #[test]
    fn zero_sized_environment_and_arguments() {
        let empty: Box<dyn FnOnce()> = Box::new(|| {});
        black_box(empty)();
        let tuple: Box<dyn FnOnce((), u64, (), u128) -> (u128, u64)> =
            Box::new(|(), small, (), wide| (wide.rotate_left(17), small ^ 91));
        let wide = (7u128 << 97) | 37;
        assert_eq!(black_box(tuple)((), 42, (), wide), (wide.rotate_left(17), 42 ^ 91));
    }

    #[repr(align(64))]
    struct Aligned<'a> { words: [u64; 9], token: Counted<'a> }

    #[test]
    fn aligned_capture_is_moved_and_destroyed() {
        let dropped = Cell::new(0);
        let value = Aligned { words: [19; 9], token: Counted(&dropped, 3) };
        let callback: Box<dyn FnOnce() -> u64 + '_> = Box::new(move || {
            let value = black_box(value);
            assert_eq!((&value as *const Aligned<'_> as usize) % 64, 0);
            let sum = value.words.iter().sum();
            drop(value.token);
            sum
        });
        assert_eq!(black_box(callback)(), 171);
        assert_eq!(dropped.get(), 3);
    }

    #[test]
    fn borrowed_capture_and_uncalled_drop() {
        let value = Cell::new(7);
        let dropped = Cell::new(0);
        let token = Counted(&dropped, 5);
        let callback: Box<dyn FnOnce(u64) + '_> = Box::new(|delta| value.set(value.get() + delta));
        black_box(callback)(31);
        let uncalled: Box<dyn FnOnce() + '_> = Box::new(move || drop(token));
        drop(black_box(uncalled));
        assert_eq!(value.get(), 38);
        assert_eq!(dropped.get(), 5);
    }

    #[test]
    fn nested_boxed_callback_return() {
        let text = String::from("nested");
        let outer: Box<dyn FnOnce(u64) -> Box<dyn FnOnce(u64) -> (String, u64)>>> =
            Box::new(move |a| Box::new(move |b| (text, a + b)));
        let inner = black_box(outer)(17);
        assert_eq!(black_box(inner)(29), (String::from("nested"), 46));
    }

    #[test]
    fn callback_vector_preserves_all_effects() {
        let observed = Cell::new(0u64);
        let dropped = Cell::new(0u64);
        let mut callbacks: Vec<Box<dyn FnOnce() + '_>> = Vec::new();
        for digit in [2, 3, 5] {
            let token = Counted(&dropped, digit);
            let observed = &observed;
            callbacks.push(Box::new(move || {
                observed.set(observed.get() * 10 + digit);
                drop(token);
            }));
        }
        for callback in black_box(callbacks) { callback(); }
        assert_eq!(observed.get(), 235);
        assert_eq!(dropped.get(), 10);
    }
}
