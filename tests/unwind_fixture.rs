use std::sync::atomic::{AtomicUsize, Ordering};
static DROPS: AtomicUsize = AtomicUsize::new(0);
struct Guard;
impl Drop for Guard {
    fn drop(&mut self) {
        DROPS.fetch_add(1, Ordering::SeqCst);
    }
}
#[inline(never)]
extern "C-unwind" fn cross_abi() {
    let _guard = Guard;
    std::panic::panic_any(123u32);
}
fn main() {
    std::panic::set_hook(Box::new(|_| {}));
    let result = std::panic::catch_unwind(|| {
        let _outer = Guard;
        cross_abi();
    });
    assert_eq!(*result.unwrap_err().downcast::<u32>().unwrap(), 123);
    let thread = std::thread::spawn(|| {
        let _guard = Guard;
        panic!("child");
    });
    assert!(thread.join().is_err());
    let mut future = std::pin::pin!(async {
        let _guard = Guard;
        panic!("future");
    });
    let mut cx = std::task::Context::from_waker(std::task::Waker::noop());
    assert!(
        std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
            std::future::Future::poll(future.as_mut(), &mut cx)
        }))
        .is_err()
    );
    assert_eq!(DROPS.load(Ordering::SeqCst), 4);
    println!("unwind-ok");
}
