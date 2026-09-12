#[repr(C)]
pub struct Record {
    pub prefix: u8,
    pub value: u64,
}
pub const SCALE: u64 = 3;
pub const LABEL: &[u8] = b"abc";
pub type Word = u64;
pub type GenericWord = u64;

#[inline(never)]
pub fn stable(seed: u64) -> u64 { seed.rotate_left(9) ^ 17 }
#[inline(never)]
pub fn body(seed: u64) -> u64 { seed.wrapping_add(7) }
#[inline(never)]
pub fn value(record: &Record) -> u64 { record.value }
#[inline(never)]
pub fn layout_metric() -> u64 {
    (std::mem::size_of::<Record>() as u64) ^ ((std::mem::align_of::<Record>() as u64) << 16)
}
#[inline(never)]
pub fn narrow(seed: u64) -> Word { seed as Word }

pub trait Adjust { fn adjust(self) -> u64; }
impl Adjust for u64 {
    #[inline(never)]
    fn adjust(self) -> u64 { self.wrapping_mul(SCALE) }
}
impl Adjust for u32 {
    #[inline(never)]
    fn adjust(self) -> u64 { (self as u64).wrapping_mul(SCALE) }
}
#[inline(never)]
pub fn generic<T: Adjust>(value: T) -> u64 { value.adjust() }
