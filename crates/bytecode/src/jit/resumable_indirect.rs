//! Dynamic layouts over the same bounded, initialized storage as direct Calls.
use super::*;

impl Assembler<'_> {
    // This cursor scratch is private to the current native call. A nested callee
    // may overwrite it only after this call has finished publishing its frame.
    fn indirect_field(&mut self, destination: u32, offset: usize) {
        self.load64(destination,19,INDIRECT_LAYOUT);
        self.load64(destination,destination,offset);
    }
    fn indirect_target(&mut self) {
        self.indirect_field(9,indirect::FUNCTION);
        self.lsl_imm(9,9,3);
        self.load64(10,19,ENTRIES);
        self.three(0x8b000000,9,10,9);
        self.load64(9,9,0);
        self.load64(16,9,0);
    }

    pub(super) fn resumable_indirect_call(
        &mut self, caller: &Function, pc: usize, pointer: Reg, args: &[Reg],
        sizes: &[usize], destination: Reg, signature: usize, functions: usize,
        profiled: bool, declines: &mut Vec<usize>,
    ) -> Result<(),EmitError> {
        // Validate the entire guest value before it indexes any host table.
        // A miss changes no guest state and consumes no bytecode instruction.
        self.get(11,pointer,true);
        self.cmp(11,31);self.decline(Cond::Ne,declines);
        self.get(13,pointer,false);
        self.imm(10,crate::FUNCTION_POINTER_TAG);
        self.three(0x8a000000,9,13,10);
        self.cmp(9,31);self.decline(Cond::Eq,declines);
        self.imm(10,!crate::FUNCTION_POINTER_TAG);
        self.three(0x8a000000,13,13,10);
        self.sub_imm(13,13,1); // null wraps to MAX and fails the unsigned bound
        self.imm(10,functions as u64);
        self.cmp(13,10);self.decline(Cond::Hs,declines);
        self.load64(14,19,INDIRECT_LAYOUTS);
        self.lsl_imm(9,13,6);
        self.three(0x8b000000,14,14,9);
        self.load64(9,14,indirect::SIGNATURE);
        self.imm(10,signature as u64);
        self.cmp(9,10);self.decline(Cond::Ne,declines);
        self.store64(14,19,INDIRECT_LAYOUT);
        // The exact signature establishes argument count/sizes and result size.
        // Entry addresses come only from host-owned, published native tables.
        self.load64(9,19,ENTRIES);
        self.lsl_imm(10,13,3);
        self.three(0x8b000000,9,9,10);
        self.load64(9,9,0);
        self.cmp(9,31);self.decline(Cond::Eq,declines);
        self.load64(16,9,0);
        self.cmp(16,31);self.decline(Cond::Eq,declines);
        protocol_mark!(self,"call_target",None);
        self.load64(9,19,state::FRAME_LEN);
        self.load64(10,19,FRAME_END);
        self.cmp(9,10);self.decline(Cond::Hs,declines);
        protocol_mark!(self,"call_frame_capacity",None);
        self.indirect_field(10,indirect::ALIGN_ADD);
        self.three(0xab000000,21,3,10);
        self.decline(Cond::Hs,declines);
        self.indirect_field(10,indirect::ALIGN_AND);
        self.three(0x8a000000,21,21,10);
        self.indirect_field(10,indirect::FRAME_SIZE);
        self.three(0xab000000,11,21,10);
        self.decline(Cond::Hs,declines);
        self.load64(10,19,MEMORY_END);
        self.cmp(11,10);self.decline(Cond::Hi,declines);
        protocol_mark!(self,"call_memory_capacity",None);
        self.load64(12,19,state::REGISTER_LEN);
        self.indirect_field(10,indirect::REGISTERS);
        self.three(0xab000000,17,12,10);
        self.decline(Cond::Hs,declines);
        self.load64(10,19,REGISTER_END);
        self.cmp(17,10);self.decline(Cond::Hi,declines);
        protocol_mark!(self,"call_register_capacity",None);
        self.lsl_imm(13,17,4);
        self.three(0xab000000,13,13,11);
        self.decline(Cond::Hs,declines);
        self.load64(10,19,WORKING_BUDGET);
        self.cmp(13,10);self.decline(Cond::Hi,declines);
        protocol_mark!(self,"call_working_budget",None);

        self.charge_transition(pc,profiled);
        protocol_mark!(self,"charge_profile",None);
        self.spill_values_at(pc+1);
        protocol_mark!(self,"call_spill",None);
        self.three(0x8b000000,11,2,3);
        self.indirect_field(9,indirect::FRAME_SIZE);
        self.three(0x8b000000,3,21,9);
        self.three(0x8b000000,12,2,3);
        self.zero_range()?;
        protocol_mark!(self,"call_frame_clear",None);
        self.load64(9,19,state::PEAK_LINEAR);
        self.cmp(3,9);self.emit(0x9a892069);
        self.store64(9,19,state::PEAK_LINEAR);
        protocol_mark!(self,"call_peak_memory",None);
        for (index,(&source,&size)) in args.iter().zip(sizes).enumerate() {
            self.address(11,source,size,false);
            protocol_mark!(self,"argument_source",Some(index));
            self.indirect_field(12,indirect::ARGUMENTS);
            self.load64(12,12,index*8);
            self.three(0x8b000000,12,21,12);
            self.three(0x8b000000,12,2,12);
            protocol_mark!(self,"argument_destination",Some(index));
            self.abi_copy(size)?;
            protocol_mark!(self,"argument_copy",Some(index));
        }
        self.imm(9,caller.registers as u64*16);
        self.three(0x8b000000,17,0,9);
        protocol_mark!(self,"call_register_cursor",None);
        self.indirect_field(9,indirect::ZEROES);
        self.cmp(9,31);let skip_clear=self.words.len();self.emit(0x54000000);
        self.mov(11,17);
        self.indirect_field(12,indirect::REGISTERS);
        self.lsl_imm(12,12,4);
        self.three(0x8b000000,12,17,12);
        self.zero_range()?;
        self.patch_conditional(skip_clear,self.words.len())?;
        protocol_mark!(self,"call_register_clear",None);
        self.get(15,destination,false);
        protocol_mark!(self,"call_result_pointer",None);
        self.resumable_save_pc(pc+1);
        self.add_imm(20,20,frame::SIZE);
        self.indirect_field(9,indirect::FUNCTION);
        self.store64(9,20,frame::FUNCTION);
        self.store64(31,20,frame::PC);
        self.store64(21,20,frame::BASE);
        self.load64(9,19,state::REGISTER_LEN);
        self.store64(9,20,frame::REGISTER_BASE);
        self.store64(15,20,frame::RETURN_ADDRESS);
        self.emit(0x39000000|((frame::TLS_CALLBACK as u32)<<10)|(20<<5)|31);
        self.indirect_field(10,indirect::REGISTERS);
        self.three(0x8b000000,9,9,10);
        self.store64(9,19,state::REGISTER_LEN);
        self.increment_cursor(state::FRAME_LEN);
        self.increment_cursor(state::CALLS);
        self.mov(0,17);self.mov(1,21);
        protocol_mark!(self,"call_publish_frame",None);
        self.switch_profile(profiled);
        protocol_mark!(self,"profile_switch",None);
        // Large register addressing can use x16. Re-read the validated target
        // only after all caller reads/spills, just as the direct Call path does.
        if caller.registers>2048 {self.indirect_target();}
        self.emit(0xd61f0200);
        protocol_mark!(self,"call_dispatch",None);
        Ok(())
    }
}
