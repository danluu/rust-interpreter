//! Fixed-size arena selection; range checks remain in checked_address().
use super::*;

impl Assembler<'_> {
    pub(super) fn select_fixed_address_space(&mut self, address: u32, write: bool) {
        #[cfg(test)]
        if !self.branch_address_spaces {
            self.imm(14, crate::heap::TAG as u64);
            self.cmp(address, 14);
            self.three(0xcb000000, 13, address, 14);
            for (dst, stack, heap) in [(address, address, 13), (17, 2, 7), (15, 3, 8), (14, 4, 31)] {
                self.emit(0x9a800000 | (heap << 16) | (3 << 12) | (stack << 5) | dst);
            }
            return;
        }
        const { assert!(crate::HEAP_POINTER_TAG == 1u64 << 62); }
        // Unsigned address >= TAG iff either top bit is set. Testing only
        // bit 62 would misclassify malformed addresses with bit 63 alone.
        // x13/x14/x15/x17 are scratch; preserve all other address/value inputs.
        self.emit(0xd3400000 | (62 << 16) | (63 << 10) | (address << 5) | 13); // lsr x13,address,#62
        let linear = self.words.len();
        self.emit(0xb400000d); // cbz x13,linear
        self.emit(0xd2800000 | (3 << 21) | (0x4000 << 5) | 14); // movz x14,#0x4000,lsl#48
        self.three(0xcb000000, address, address, 14); // exact subtraction, not tag masking
        self.mov(17, 7);
        self.mov(15, 8);
        if write { self.mov(14, 31); }
        let ready = self.words.len();
        self.emit(0x14000000);
        self.words[linear] |= branch_displacement(linear, self.words.len(), 19,
            CodegenLimit::ConditionalBranch).expect("bounded arena selector") << 5;
        self.mov(17, 2);
        self.mov(15, 3);
        if write { self.mov(14, 4); }
        self.words[ready] |= branch_displacement(ready, self.words.len(), 26,
            CodegenLimit::Jump).expect("bounded arena selector");
    }
}

#[cfg(test)]
mod tests;
