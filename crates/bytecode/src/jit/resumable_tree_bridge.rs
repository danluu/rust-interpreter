//! Bounded native adapter. Stronger admission falls through to ordinary Call.
use super::*;
use tree_bridge::layout as bridge;

impl Assembler<'_> {
    pub(super) fn bridge_preflight(&mut self, plan: trees::Plan) -> Vec<usize> {
        let mut ordinary = vec![];
        self.imm(10,plan.instructions+1);
        self.cmp(BUDGET_REGISTER,10);self.decline(Cond::Lo,&mut ordinary);
        self.load64(9,19,state::FRAME_LEN);
        self.imm(10,plan.depth as u64);self.three(0xab000000,9,9,10);
        self.decline(Cond::Hs,&mut ordinary);
        self.load64(10,19,FRAME_END);self.cmp(9,10);self.decline(Cond::Hi,&mut ordinary);
        self.imm(10,plan.frame_align as u64-1);
        self.three(0xab000000,21,3,10);self.decline(Cond::Hs,&mut ordinary);
        self.imm(10,!(plan.frame_align as u64-1));self.three(0x8a000000,21,21,10);
        self.imm(10,plan.frame_span as u64);self.three(0xab000000,11,21,10);
        self.decline(Cond::Hs,&mut ordinary);
        self.load64(10,19,MEMORY_END);self.cmp(11,10);self.decline(Cond::Hi,&mut ordinary);
        self.load64(12,19,state::REGISTER_LEN);
        self.imm(10,plan.register_slots as u64);self.three(0xab000000,17,12,10);
        self.decline(Cond::Hs,&mut ordinary);
        self.load64(10,19,REGISTER_END);self.cmp(17,10);self.decline(Cond::Hi,&mut ordinary);
        // REGISTER_END bounds a real initialized Vec<u128>; this shift fits.
        self.lsl_imm(13,17,4);self.three(0xab000000,13,13,11);
        self.decline(Cond::Hs,&mut ordinary);
        self.load64(10,19,WORKING_BUDGET);self.cmp(13,10);self.decline(Cond::Hi,&mut ordinary);

        ordinary
    }

    pub(super) fn resumable_tree_call(
        &mut self, caller: &Function, pc: usize, id: usize, callee: &Function,
        args: &[Reg], slots: Option<&[Option<usize>]>, destination: Reg,
        zeroes: bool, profiled: bool, plan: trees::Plan, target: usize, global_start: usize,
    ) -> Result<(), EmitError> {
        let ordinary = self.bridge_preflight(plan);

        // Preserve ordinary root Call order. Every failure before the host
        // frame below goes straight to the original resumable fault tail.
        self.charge_transition(pc,profiled);
        self.spill_values_at(pc+1);
        self.three(0x8b000000,11,2,3);
        self.imm(9,callee.frame_size.max(1) as u64);self.three(0x8b000000,3,21,9);
        self.three(0x8b000000,12,2,3);self.clear_call_frame(caller,callee)?;
        self.load64(9,19,state::PEAK_LINEAR);self.cmp(3,9);
        self.emit(0x9a892069);self.store64(9,19,state::PEAK_LINEAR);
        for (index,(source,slot)) in args.iter().zip(&callee.args).enumerate() {
            self.call_argument_address(*source,slot.size,slots.and_then(|s|s.get(index).copied()).flatten())?;
            self.imm(12,slot.offset as u64);self.three(0x8b000000,12,21,12);
            self.three(0x8b000000,12,2,12);self.abi_copy(slot.size)?;
        }
        self.imm(9,caller.registers as u64*16);self.three(0x8b000000,17,0,9);
        if zeroes {
            self.mov(11,17);self.imm(12,callee.registers as u64*16);
            self.three(0x8b000000,12,17,12);self.zero_range_at_least(callee.registers*16)?;
        }
        self.get(15,destination,false);
        self.resumable_save_pc(pc+1);
        // x19 remains the shared resumable cursor. The complete tree saves
        // and restores x20, so this frame stores the old count/profile instead.
        self.load64(10,19,state::CALLS);
        if profiled { self.load64(9,19,8); } else { self.mov(9,31); }
        self.push_pair(10,9,48);
        self.stack_pair(false,0,1,16);
        self.stack_pair(false,22,30,32);
        self.add_imm(10,10,1);self.store64(10,19,state::CALLS);
        self.add_imm(9,20,frame::SIZE);self.store64(9,19,BRIDGE+bridge::FRAMES);
        self.imm(9,1);self.store64(9,19,BRIDGE+bridge::DEPTH);
        self.store64(31,19,BRIDGE+bridge::FAULT_DEPTH);
        self.store64(31,19,BRIDGE+bridge::FAULT_REGISTER_END);
        if profiled {
            self.load64(9,19,BRIDGE+40);
            self.imm(10,id as u64*8);self.three(0x8b000000,9,9,10);
            self.load64(9,9,0);self.store64(9,19,8);
        }
        self.mov(0,17);self.mov(1,21);
        let at=global_start.checked_add(self.words.len()).ok_or(EmitError::Limit(CodegenLimit::Jump))?;
        if target>=global_start {return Err(EmitError::InvalidRelocation("bridge target is not published"));}
        self.emit(0x94000000|branch_displacement(at,target,26,CodegenLimit::Jump)?);

        // x22 already contains the consumed guest budget; calls and peak are
        // in the shared state. Restore only caller pointers/profile and host LR.
        self.mov(16,0);
        self.load64(10,19,state::CALLS);self.load64(9,31,0);
        self.three(0xcb000000,10,10,9); // successful nested + root Calls
        self.load64(11,19,BRIDGE+bridge::FAULT_DEPTH);
        self.load64(12,19,BRIDGE+bridge::FAULT_REGISTER_END);
        self.load64(9,31,32);self.three(0xcb000000,9,9,22);
        self.load64(14,19,BRIDGE_INSTRUCTIONS);self.three(0x8b000000,9,9,14);
        self.store64(9,19,BRIDGE_INSTRUCTIONS);
        self.load64(9,19,BRIDGE_CALLS);self.three(0x8b000000,9,9,10);self.store64(9,19,BRIDGE_CALLS);
        self.increment_cursor(BRIDGE_ENTRIES);
        self.three(0xcb000000,14,10,11); // completed returns = pushes - active depth
        self.load64(9,19,state::RETURNS);self.three(0x8b000000,9,9,14);self.store64(9,19,state::RETURNS);
        if profiled {self.load64(9,31,8);self.store64(9,19,8);}
        self.stack_pair(true,0,1,16);
        self.load64(30,31,40);
        self.add_imm(31,31,48); // discard only this adapter's host frame
        self.cmp(16,31);
        let success=self.words.len();self.emit(0x54000000);
        self.load64(9,19,state::FRAME_LEN);self.three(0x8b000000,9,9,11);self.store64(9,19,state::FRAME_LEN);
        self.store64(12,19,state::REGISTER_LEN);
        self.mov(0,16);self.return_to_vm();
        self.patch_conditional(success,self.words.len())?;
        self.successor(pc+1);
        // This label is the original stronger-guard decline: no debit, copy,
        // profile increment or active descriptor change has occurred.
        let fallback=self.words.len();
        for at in ordinary {self.patch_conditional(at,fallback)?;}
        Ok(())
    }
}
