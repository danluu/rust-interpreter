pub type Word = u32;

pub const WIDTH: usize = 2;

pub fn value() -> Word {
    5 // changed dependency body
}

pub trait Convert {
    fn to_word(&self) -> Word;
}

impl Convert for u32 {
    fn to_word(&self) -> Word {
        *self as Word
    }
}

#[macro_export]
macro_rules! macro_value {
    () => { 13u32 };
}
