//! Exact eight-byte local ranges whose current bits are still held in x9.
//! Facts expire at every control transfer, possible clobber and aliasing write.

const CAPACITY: usize = 16;

pub(super) struct State {
    enabled: bool,
    offsets: [usize; CAPACITY],
    len: usize,
}

impl Default for State {
    fn default() -> Self { Self::new(true) }
}

impl State {
    pub fn new(enabled: bool) -> Self { Self {enabled, offsets:[0; CAPACITY], len:0} }
    pub fn word(&mut self, word: u32) {
        if self.len != 0 && !preserves_x9(word) { self.len=0; }
    }
    pub fn contains(&self, offset: Option<usize>, size: usize) -> bool {
        self.enabled && size==8 && offset.is_some_and(|o|self.offsets[..self.len].contains(&o))
    }
    pub fn capture(&mut self, offset: Option<usize>, size: usize) {
        if !self.enabled || size!=8 { return; }
        let Some(offset)=offset else { return; };
        if offset.checked_add(8).is_none() { return; }
        if self.offsets[..self.len].contains(&offset) { return; }
        if self.len==CAPACITY {
            self.offsets.copy_within(1..CAPACITY,0);
            self.len-=1;
        }
        self.offsets[self.len]=offset;self.len+=1;
    }
    pub fn invalidate(&mut self, offset: Option<usize>, size: usize) {
        if self.len==0 || size==0 { return; }
        let Some(offset)=offset else {self.len=0;return;};
        let Some(end)=offset.checked_add(size) else {self.len=0;return;};
        let mut keep=0;
        for i in 0..self.len {
            let previous=self.offsets[i];
            if previous>=end || previous.checked_add(8).is_some_and(|e|offset>=e) {
                self.offsets[keep]=previous;keep+=1;
            }
        }
        self.len=keep;
    }
}

/// Only reviewed no-writeback instruction classes preserve the scratch value.
/// Stores preserve the register; typed operation effects invalidate memory facts.
pub(super) fn preserves_x9(word: u32) -> bool {
    let rd=word&31;
    // These exact transfers write SIMD registers, leaving every GPR intact.
    if matches!(word&0xfffffc00,0x1e270000|0x9e670000|0x4e181c00) {return true;}
    // Unsigned-offset SIMD loads/stores have no base writeback and no GPR
    // destination. Typed memory effects still invalidate aliased byte ranges.
    if word&0x3b000000==0x39000000 && word&0x04000000!=0 {return true;}
    if word==0xd503201f {return true;}
    if word&0x1f000000==0x11000000 || matches!(word&0x1f000000,0x0a000000|0x0b000000) {
        return rd!=9;
    }
    if matches!(word&0x1f800000,0x12800000|0x13000000|0x13800000) {return rd!=9;}
    if word&0x3b000000==0x39000000 && word&0x04000000==0 {
        return (word>>22)&3==0 || rd!=9;
    }
    if word&0x3b800000==0x29000000 && word&0x04000000==0 {
        return word&(1<<22)==0 || (rd!=9 && (word>>10)&31!=9);
    }
    false
}

#[cfg(test)]
#[path="scratch_values_tests.rs"]
mod tests;
