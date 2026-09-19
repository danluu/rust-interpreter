//! Small case tables still compare the complete 128-bit guest value.
use super::{Assembler,EmitError};

impl Assembler<'_> {
    // x9/x10 contain the low/high halves. A miss falls through to the caller's
    // existing default successor. No case is reordered, including duplicates.
    pub(super) fn switch_cases(&mut self,cases:&[(u128,usize)])->Result<(),EmitError> {
        if let [(0,target)]=cases {
            self.three(0xaa000000,11,9,10); // orr x11,x9,x10
            self.cmp(11,31);
            let miss=self.words.len();self.emit(0x54000001);
            self.successor(*target);
            self.patch_conditional(miss,self.words.len())?;
        } else if !cases.is_empty() && cases.iter().all(|(value,_)|*value<=4095) {
            // A nonzero upper half cannot match any case in this table. Test it
            // once; each low-half comparison then has the full-width meaning.
            self.cmp(10,31);
            let wide=self.words.len();self.emit(0x54000001);
            for (value,target) in cases {
                self.emit(0xf100001f | ((*value as u32)<<10) | (9<<5)); // cmp x9,#imm12
                let miss=self.words.len();self.emit(0x54000001);
                self.successor(*target);
                self.patch_conditional(miss,self.words.len())?;
            }
            self.patch_conditional(wide,self.words.len())?;
        } else {
            // General case constants retain the original two-half comparison.
            for (case,target) in cases {
                self.imm(11,*case as u64);self.cmp(9,11);
                let low=self.words.len();self.emit(0x54000001);
                self.imm(11,(*case>>64) as u64);self.cmp(10,11);
                let high=self.words.len();self.emit(0x54000001);
                self.successor(*target);
                let next=self.words.len();
                self.patch_conditional(low,next)?;self.patch_conditional(high,next)?;
            }
        }
        Ok(())
    }
}

#[cfg(test)]
#[path="compact_switch_tests.rs"]
mod tests;
