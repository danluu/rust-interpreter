//! Private metadata for a complete tree entered from a resumable Call.
//! No guest address can name this cursor or the prepared descriptor array.
use super::*;
use crate::frames::{Frame,layout as frame};
use crate::native_continuation::{Capacity,State};
use native_calls::TreeCursor;

#[repr(C)]
pub(super) struct BridgeCursor {
    pub tree: TreeCursor,
    pub frames: *mut Frame,
    pub registers: *mut u128,
    pub depth: usize,
    pub fault_depth: usize,
    pub fault_register_end: usize,
}

pub(super) mod layout {
    use super::*;
    pub const FRAMES:usize=std::mem::offset_of!(BridgeCursor,frames);
    pub const REGISTERS:usize=std::mem::offset_of!(BridgeCursor,registers);
    pub const DEPTH:usize=std::mem::offset_of!(BridgeCursor,depth);
    pub const FAULT_DEPTH:usize=std::mem::offset_of!(BridgeCursor,fault_depth);
    pub const FAULT_REGISTER_END:usize=std::mem::offset_of!(BridgeCursor,fault_register_end);
    // The tree host frame already leaves this eight-byte slot unused after
    // its saved profile pointer. It belongs to the current function only.
    pub const HOST_PC:usize=56;
    #[cfg(all(target_arch="aarch64",target_os="macos"))]
    const _:()={
        assert!(std::mem::offset_of!(BridgeCursor,tree)==0);
        assert!(FRAMES==80 && REGISTERS==88 && DEPTH==96);
        assert!(FAULT_DEPTH==104 && FAULT_REGISTER_END==112);
        assert!(std::mem::size_of::<BridgeCursor>()==120);
    };
}

/// Reference for the emitted preflight. All quantities include the root tree;
/// the outer Call is charged separately. A failed stronger guard is a decline.
pub(super) fn admission(plan:trees::Plan,state:State,capacity:Capacity,working_budget:usize)
    -> Option<trees::Requirements>
{
    if state.remaining<plan.instructions.checked_add(1)? {return None;}
    let need=plan.requirements(state.memory_len,state.register_len,state.frame_len)?;
    if need.memory_end>capacity.memory || need.register_end>capacity.registers || need.frames>capacity.frames {
        return None;
    }
    if need.register_end.checked_mul(16)?.checked_add(need.memory_end)?>working_budget {return None;}
    Some(need)
}

impl Assembler<'_> {
    pub(super) fn bridge_enter_child(&mut self) {
        if self.tree_bridge_frame.is_none() {return;}
        self.imm(9,(self.current_pc+1) as u64);
        self.store64(9,31,layout::HOST_PC);
        self.load64(9,19,layout::DEPTH);
        self.add_imm(9,9,1);
        self.store64(9,19,layout::DEPTH);
    }

    pub(super) fn bridge_leave_tree_frame(&mut self) {
        if self.tree_bridge_frame.is_none() {return;}
        self.load64(9,19,layout::DEPTH);
        self.sub_imm(9,9,1);
        self.store64(9,19,layout::DEPTH);
    }

    /// Materialize only on terminal failure, while this function's bounded
    /// host frame still contains its original entry pointers and continuation.
    /// Preserve x0 (fault), x1–x8 (guest arenas) and x19–x30 (host/tree state).
    pub(super) fn bridge_fault_frame(&mut self) -> Result<(),EmitError> {
        let Some((function,registers))=self.tree_bridge_frame else {return Ok(());};
        self.load64(9,31,32); // saved function-entry register pointer
        self.load64(10,19,layout::REGISTERS);
        self.three(0xcb000000,9,9,10);
        self.emit(0xd340fc00|(4<<16)|(9<<5)|9); // lsr x9,x9,#4: absolute slot base
        self.load64(10,19,layout::DEPTH);
        self.sub_imm(11,10,1);
        self.imm(12,frame::SIZE as u64);
        self.three(0x9b007c00,11,11,12);
        self.load64(12,19,layout::FRAMES);
        self.three(0x8b000000,11,11,12); // prechecked descriptor for this depth
        self.imm(12,function as u64);
        self.store64(12,11,frame::FUNCTION);
        self.load64(12,31,layout::HOST_PC);
        self.store64(12,11,frame::PC);
        self.load64(12,31,40); // saved function-entry guest base
        self.store64(12,11,frame::BASE);
        self.store64(9,11,frame::REGISTER_BASE);
        self.store64(20,11,frame::RETURN_ADDRESS);
        self.emit(0x39000000|((frame::TLS_CALLBACK as u32)<<10)|(11<<5)|31);
        self.load64(12,19,layout::FAULT_DEPTH);
        self.cmp(12,31);
        let recorded=self.words.len();self.emit(0x54000001); // b.ne already captured
        self.store64(10,19,layout::FAULT_DEPTH);
        self.imm(12,registers as u64);
        self.three(0x8b000000,9,9,12);
        self.store64(9,19,layout::FAULT_REGISTER_END);
        self.patch_conditional(recorded,self.words.len())?;
        self.bridge_leave_tree_frame();
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn bridge_preflight_matches_wide_integer_bounds_and_includes_outer_call() {
        let plan=trees::Plan {instructions:19,depth:3,frame_span:145,register_slots:17,frame_align:64};
        for memory in [0,1,63,64,65,usize::MAX-64,usize::MAX] {
            for registers in [0,1,19,usize::MAX/16,usize::MAX] {
                for frames in [0,1,7,usize::MAX] {
                    for budget in [0,19,20,u64::MAX] {
                        for cap in [0,16,256,1024,usize::MAX] {
                            let state=State {remaining:budget,profile_hits:std::ptr::null_mut(),memory_len:memory,
                                peak_linear:memory,register_len:registers,frame_len:frames,calls:0,returns:0};
                            let capacity=Capacity {memory:cap,registers:cap,frames:cap};
                            let base=(memory as u128+63)&!63;
                            let end=base+145;let reg_end=registers as u128+17;let depth=frames as u128+3;
                            let expected=budget>=20 && end<=cap as u128 && reg_end<=cap as u128
                                && depth<=cap as u128 && end+reg_end*16<=cap as u128;
                            let got=admission(plan,state,capacity,cap);
                            assert_eq!(got.is_some(),expected);
                            if let Some(got)=got {assert_eq!((got.root_base as u128,got.memory_end as u128,
                                got.register_end as u128,got.frames as u128),(base,end,reg_end,depth));}
                        }
                    }
                }
            }
        }
    }
}
