//! Speculative whole-range validation with an unchanged-entry VM fallback.
use super::*;
use range_groups::{Plan, Root};

impl<'a> Assembler<'a> {
    pub(super) fn prepare_guarded_range(&mut self, plan: Option<&'a Plan>) -> Result<Vec<usize>, EmitError> {
        let Some(plan)=plan else { return Ok(vec![]); };
        debug_assert!(self.resumable && self.failures.is_empty());
        match plan.root {
            Root::Register(reg) => self.get(11,reg,false),
            Root::FrameSlot(offset) => {
                debug_assert!(offset.checked_add(8).is_some_and(|end|end<=self.frame_size));
                self.materialize(11,Fact::Local(offset),false);
                self.three(0x8b000000,11,2,11);
                self.emit(0xf940016b); // ldr x11,[x11]: initialized entry slot
            }
        }
        let mut declines=vec![];
        let branch=|a:&mut Self,condition:u32,declines:&mut Vec<usize>| {
            declines.push(a.words.len());a.emit(0x54000000|condition);
        };
        if plan.low<0 {
            self.imm(9,plan.low.unsigned_abs());self.cmp(11,9);
            branch(self,3,&mut declines); // unsigned underflow
            self.three(0xcb000000,11,11,9);
        } else if plan.low>0 {
            self.imm(9,plan.low as u64);self.three(0xab000000,11,11,9);
            branch(self,2,&mut declines); // addition carry
        }
        let span=(plan.high-plan.low) as usize;
        self.imm(10,span as u64);
        self.three(0xab000000,12,11,10);
        branch(self,2,&mut declines); // whole logical end must not wrap
        if self.heap {
            self.imm(14,crate::heap::TAG as u64);
            self.cmp(11,14);
            let heap=self.words.len();self.emit(0x54000002); // start >= TAG
            self.cmp(12,14);
            branch(self,8,&mut declines); // stack range crosses TAG
            self.patch_conditional(heap,self.words.len())?;
        }
        // A failed stronger check is a decline, never an early guest fault.
        self.checked_address(11,span,plan.writes);
        declines.extend(std::mem::take(&mut self.failures).into_iter().map(|(pc,_)|pc));
        if plan.frame_disjoint {
            self.three(0x8b000000,12,2,1); // host frame start
            self.imm(10,span as u64);self.three(0x8b000000,10,11,10);
            self.cmp(10,12);
            let before=self.words.len();self.emit(0x54000009); // group end <= frame start
            self.imm(10,self.frame_size as u64);self.three(0x8b000000,12,12,10);
            self.cmp(11,12);branch(self,3,&mut declines); // group starts inside/before frame end
            self.patch_conditional(before,self.words.len())?;
        }
        self.emit(0x9e670170); // fmov d16,x11; complete validated host range base
        self.guarded_range=Some(plan);
        Ok(declines)
    }

    pub(super) fn guarded_displacement(&mut self, reg: Reg, size: usize, write: bool) -> Option<usize> {
        let offset=self.guarded_range.as_ref()?.displacement(self.current_pc,reg,size,write)?;
        // get() also records live-in use. Preserve that effect when its actual
        // register load/translation is replaced, including linked backedges.
        if !self.defined.contains(&reg) { self.live_in.insert(reg); }
        Some(offset)
    }

    pub(super) fn guarded_base(&mut self, rd: u32) {
        // v16 is caller-saved and unused by the audited region operations.
        // No cache survives a region edge, guest Call or VM return.
        self.emit(0x9e660000|(16<<5)|rd); // fmov Xd,d16
    }
}

#[cfg(all(test,target_arch="aarch64",target_os="macos"))]
mod tests;
