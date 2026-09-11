use std::sync::atomic::{AtomicUsize, Ordering};
use std::cell::Cell;

const OFFSET: i64 = 3;
#[repr(C)]
struct Record { a: u64, b: u32 }
static DROPS: AtomicUsize = AtomicUsize::new(0);
thread_local! { static TLS: Cell<u32> = const { Cell::new(17) }; }
struct Guard;
impl Drop for Guard { fn drop(&mut self) { DROPS.fetch_add(1, Ordering::SeqCst); } }
trait Eval { fn eval(&self, x: i64) -> i64; }
impl Eval for Record { fn eval(&self, x: i64) -> i64 { x + self.a as i64 + self.b as i64 } }
#[inline(never)] fn choose_a(x: i64) -> i64 { x * 2 }
#[inline(never)] fn choose_b(x: i64) -> i64 { x * 3 }
#[inline(never)] fn call_target(x: i64) -> i64 { choose_a(x) }
#[inline(never)] fn generic<const N: usize>(x: i64) -> [i64; N] { [x + OFFSET; N] }
unsafe extern "C" { fn abs(x: i32) -> i32; }

fn main() {
    let record = Record { a: 42, b: 7 };
    let object: &dyn Eval = &record;
    let closure = |x| object.eval(x) + OFFSET;
    let guard = Guard;
    let array = generic::<5>(9);
    let child = std::thread::spawn(|| TLS.with(|x| { x.set(23); x.get() }));
    drop(guard);
    let future = async { array.iter().sum::<i64>() };
    let mut future = std::pin::pin!(future);
    let mut context = std::task::Context::from_waker(std::task::Waker::noop());
    let value = std::future::Future::poll(future.as_mut(), &mut context);
    println!("{} {} {} {} {} {} {:?} {} {} {:.3}",
        call_target(7), closure(5), std::mem::size_of::<Record>(),
        DROPS.load(Ordering::SeqCst), TLS.with(Cell::get), child.join().unwrap(),
        value, unsafe { abs(-15) }, choose_a(2) + choose_b(2), 2.5f64.sqrt());
}
