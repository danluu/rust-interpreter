worker_macros::value!();
include!(concat!(env!("OUT_DIR"), "/value.rs"));
core::arch::global_asm!("");

static mut SCRATCH: [u64; 2] = [5, 9];

pub fn answer() -> u64 {
    let mut values = Box::new([worker_shared::value(), 2]);
    values[1] += values[0];
    unsafe {
        let scratch = &raw mut SCRATCH;
        (*scratch)[0] = values[1];
        (*scratch)[1] += (*scratch)[0];
        (*scratch)[1] + HOST_VALUE + MACRO_VALUE
    }
}

pub fn assembly() -> u64 {
    unsafe { core::arch::asm!("", options(nomem, nostack)); }
    0
}
