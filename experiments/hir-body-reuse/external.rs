pub struct Foreign;
pub trait Left { fn selected(&self) -> u32; }
pub trait Right { fn selected(&self) -> u32; }
impl Left for Foreign { fn selected(&self) -> u32 { 11 } }
impl Right for Foreign { fn selected(&self) -> u32 { 22 } }
pub fn identity(x: i64) -> i64 { x }
