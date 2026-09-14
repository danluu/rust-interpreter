//! Opt-in native-to-native transactions for bounded confined scalar leaves.
//! Preparation uses the shared arena, before native entry. No host callback is
//! reachable from a generated Call; guards and private failure replay it whole.
use super::*;
use super::resumable::{self, Cond, BUDGET_REGISTER};
use crate::native_continuation::layout as state;
use crate::{proof, scalar_ir};

fn memory_plan(program:&Program,id:usize,work:&mut usize)->proof::MemoryPlan {
    #[cfg(all(test,target_arch="aarch64",target_os="macos"))]
    if crate::scalar_call_model::native_stores_enabled() {return proof::memory_plan_transaction(program,id,work);}
    proof::memory_plan_for_call(program,id,work)
}
fn emit(plan:&scalar_ir::Plan,profiled:bool,heap:bool)->Result<scalar_ir::native_leaf::Emitted,&'static str> {
    #[cfg(all(test,target_arch="aarch64",target_os="macos"))]
    if crate::scalar_call_model::native_stores_enabled() {return scalar_ir::native_leaf::emit_call_transaction(plan,profiled,heap);}
    scalar_ir::native_leaf::emit_call_with_heap(plan,profiled,heap)
}

pub(super) struct State {
    tried: Vec<bool>,
    pub entries: Vec<Option<Entry>>,
    proof_work: usize,
    scalar_work: usize,
}
#[derive(Clone, Copy)]
pub(super) struct Entry {
    pub offset: usize,
    pub bytes: usize,
    maximum_steps: usize,
    success_steps: Option<usize>,
    target: usize,
}
impl Jit<'_> {
    pub(crate) fn enable_scalar_calls(&mut self) {
        assert!(self.resumable.is_some() && self.scalar.is_none());
        self.scalar = Some(State {tried:vec![false;self.program.functions.len()],
            entries:vec![None;self.program.functions.len()],proof_work:proof::MAX_GLOBAL_WORK,scalar_work:128_000_000});
    }
    pub(super) fn scalar_entry(&self,id:usize)->Option<Entry> {self.scalar.as_ref()?.entries[id]}
    #[cfg(test)]
    pub(super) fn observe_saved_scalar_entry(&mut self,id:usize,offset:usize,bytes:usize,base:usize)->Vec<u32> {
        // Recreate only immutable emission metadata for an already SHA-bound
        // saved arena. No Code allocation, append or executable publication.
        assert!(self.code.is_none() && self.bytes==0 && self.scalar_entry(id).is_none());
        assert!(offset%4==0 && bytes>0 && bytes%4==0 && offset.checked_add(bytes).is_some_and(|end|end<=self.capacity));
        let mut work=proof::MAX_GLOBAL_WORK;
        let memory=memory_plan(self.program,id,&mut work);
        let plan=scalar_ir::lower(&self.program.functions[id],&memory,250_000).unwrap();
        let emitted=emit(&plan,self.profiled,self.uses_heap).unwrap();
        assert_eq!(emitted.words.len()*4,bytes);
        self.scalar.as_mut().unwrap().entries[id]=Some(Entry {offset,bytes,
            maximum_steps:plan.maximum_steps,success_steps:emitted.success_steps,
            target:base.checked_add(offset).unwrap()});
        emitted.words
    }
    pub(super) fn prepare_scalar_callees(&mut self,id:usize)->Result<(),String> {
        for pc in 0..self.program.functions[id].code.len() {
            let Op::Call{function,..}=self.program.functions[id].code[pc] else {continue;};
            self.prepare_scalar(function)?;
        }
        Ok(())
    }
    fn prepare_scalar(&mut self,id:usize)->Result<(),String> {
        let scalar=self.scalar.as_mut().unwrap();
        if scalar.tried[id] {return Ok(());}scalar.tried[id]=true;
        let f=&self.program.functions[id];
        // Bound host Call scratch independently of scalar SSA spill storage.
        if f.args.len()>64 || self.bytes>=self.capacity {return Ok(());}
        let memory=memory_plan(self.program,id,&mut scalar.proof_work);
        let limit=scalar.scalar_work.min(250_000);
        let plan=scalar_ir::lower(f,&memory,limit);
        scalar.scalar_work=scalar.scalar_work.saturating_sub(match &plan {Ok(p)=>p.work,Err("no_memory_plan")=>0,Err(_)=>limit});
        let Ok(plan)=plan else {return Ok(());};
        let Ok(emitted)=emit(&plan,self.profiled,self.uses_heap) else {return Ok(());};
        let bytes=emitted.words.len()*4;
        if bytes>self.capacity-self.bytes {return Ok(());}
        if self.code.is_none() {self.code=Some(platform::Code::reserve(self.capacity)?);}
        let offset=self.code.as_mut().unwrap().append(&emitted.words)?;
        let target=self.code.as_ref().unwrap().published().0+offset;
        scalar.entries[id]=Some(Entry{offset,bytes,maximum_steps:plan.maximum_steps,success_steps:emitted.success_steps,target});
        self.bytes+=bytes;
        Ok(())
    }
    pub(super) fn reconstruct_scalar(&self,id:usize)->Result<Vec<u32>,String> {
        let entry=self.scalar_entry(id).ok_or("missing scalar entry")?;
        let mut work=proof::MAX_GLOBAL_WORK;
        let memory=memory_plan(self.program,id,&mut work);
        let plan=scalar_ir::lower(&self.program.functions[id],&memory,250_000).map_err(str::to_string)?;
        if plan.maximum_steps!=entry.maximum_steps {return Err("scalar reconstruction budget mismatch".into());}
        let emitted=emit(&plan,self.profiled,self.uses_heap).map_err(str::to_string)?;
        if emitted.success_steps!=entry.success_steps {return Err("scalar reconstruction success-count mismatch".into());}
        if emitted.words.len()*4!=entry.bytes {return Err("scalar reconstruction extent mismatch".into());}
        Ok(emitted.words)
    }
}

const OUTPUT:usize=scalar_ir::native_leaf::CALL_OUTPUT;
const ARGUMENTS:usize=scalar_ir::native_leaf::CALL_ARGUMENTS;
const _:()={assert!(std::mem::size_of::<scalar_ir::native_leaf::Output>()==96);};
impl Assembler<'_> {
    fn scalar_guard_address(&mut self,address:u32,size:usize,write:bool,declines:&mut Vec<usize>) {
        let prior=self.failures.len();
        self.checked_address(address,size,write);
        // These are eligibility guards. Their failure must not publish the
        // Memory fault earlier than the original Call/callee/Return sequence.
        declines.extend(self.failures.drain(prior..).map(|(at,kind)|{assert!(kind==Failure::Memory);at}));
    }
    fn scalar_restore(&mut self,stack:usize) {
        for (reg,offset) in [(3,24),(30,32)] {self.load64(reg,31,offset);}
        self.add_imm(31,31,stack);
    }
    #[allow(clippy::too_many_arguments)]
    pub(super) fn scalar_call(&mut self,pc:usize,id:usize,f:&Function,args:&[Reg],slots:Option<&[Option<usize>]>,destination:Reg,
        entry:Entry,profiled:bool)->Result<(),EmitError> {
        let mut before=vec![];let mut private=vec![];
        self.imm(9,entry.maximum_steps as u64+1);
        self.cmp(BUDGET_REGISTER,9);self.decline(Cond::Lo,&mut before);
        self.load64(9,19,state::FRAME_LEN);self.load64(10,19,resumable::FRAME_END);
        self.cmp(9,10);self.decline(Cond::Hs,&mut before);
        self.imm(10,f.frame_align as u64-1);
        self.three(0xab000000,21,3,10);self.decline(Cond::Hs,&mut before);
        self.imm(10,!(f.frame_align as u64-1));self.three(0x8a000000,21,21,10);
        self.imm(10,f.frame_size.max(1) as u64);
        self.three(0xab000000,11,21,10);self.decline(Cond::Hs,&mut before);
        self.load64(10,19,resumable::MEMORY_END);self.cmp(11,10);self.decline(Cond::Hi,&mut before);
        self.load64(12,19,state::REGISTER_LEN);self.imm(10,f.registers as u64);
        self.three(0xab000000,17,12,10);self.decline(Cond::Hs,&mut before);
        self.load64(10,19,resumable::REGISTER_END);self.cmp(17,10);self.decline(Cond::Hi,&mut before);
        self.lsl_imm(13,17,4);self.three(0xab000000,13,13,11);self.decline(Cond::Hs,&mut before);
        self.load64(10,19,resumable::WORKING_BUDGET);self.cmp(13,10);self.decline(Cond::Hi,&mut before);

        let stack=ARGUMENTS+args.len()*16;assert!(stack%16==0 && stack<4096);
        self.sub_imm(31,31,stack);
        for (reg,offset) in [(3,24),(30,32),(11,48)] {self.store64(reg,31,offset);}
        if f.result.size!=0 {self.get(11,destination,false);self.scalar_guard_address(11,f.result.size,true,&mut private);self.store64(11,31,40);}
        for (index,(&source,slot)) in args.iter().zip(&f.args).enumerate() {
            if slot.size==0 {continue;} // No input lane exists for a zero-byte argument.
            let prior=self.failures.len();
            // Equality with a bounded caller-frame slot permits direct host
            // addressing. A stale hint takes the original checked path; an
            // invalid address declines the whole transaction before any commit.
            self.call_argument_address(source,slot.size,slots.and_then(|s|s[index]))?;
            private.extend(self.failures.drain(prior..).map(|(at,kind)|{assert!(kind==Failure::Memory);at}));
            // The scalar emitter reads no high half for an input <= 8 bytes.
            // Keep the exact address guard and low-byte read, including odd widths.
            self.load_mem(9,if slot.size>8 {10} else {31},11,slot.size);
            self.store64(9,31,ARGUMENTS+index*16);
            if slot.size>8 {self.store64(10,31,ARGUMENTS+index*16+8);}
        }
        // Private leaf inputs and Output live at fixed caller-SP offsets;
        // x21 is the prechecked logical base. x0–x2, x4–x8 and x19–x29 stay
        // live. Only the allocator's x3 and the link register need restoring.
        self.imm(16,entry.target as u64);
        self.emit(0xd63f0200); // blr x16: one nonrecursive native leaf
        self.cmp(9,31);self.decline(Cond::Ne,&mut private);

        // Restore the parent's live ABI while retaining private output. No
        // fallible action follows success; this is the transaction commit.
        for (reg,offset) in [(3,24),(30,32)] {self.load64(reg,31,offset);}
        self.charge_transition(pc,profiled);
        if let Some(steps)=entry.success_steps {self.sub_imm(BUDGET_REGISTER,BUDGET_REGISTER,steps);}
        else {self.load64(9,31,OUTPUT+16);self.three(0xcb000000,BUDGET_REGISTER,BUDGET_REGISTER,9);}
        self.three(0x8b000000,11,2,3);self.three(0x8b000000,12,2,21);
        self.zero_range()?; // retain exactly the ordinary Call's zeroed padding
        if f.result.size!=0 {
            self.load64(9,31,OUTPUT);self.load64(10,31,OUTPUT+8);self.load64(12,31,40);
            self.store_mem(9,10,12,f.result.size);
        }
        self.load64(10,31,48);self.load64(9,19,state::PEAK_LINEAR);self.cmp(10,9);
        self.emit(0x9a892149); // csel x9,x10,x9,hs
        self.store64(9,19,state::PEAK_LINEAR);
        self.mov(3,21);
        self.increment_cursor(state::CALLS);self.increment_cursor(state::RETURNS);
        if profiled {self.scalar_profile(id,f.code.len())?;}
        self.add_imm(31,31,stack);
        self.successor(pc+1);

        let restore=self.words.len();
        for at in private {self.patch_conditional(at,restore)?;}
        self.scalar_restore(stack);
        let fallback=self.words.len();
        for at in before {self.patch_conditional(at,fallback)?;}
        Ok(())
    }
    fn scalar_profile(&mut self,id:usize,code_len:usize)->Result<(),EmitError> {
        self.load64(12,19,resumable::SCALAR_PROFILES);
        self.imm(9,id as u64*8);self.three(0x8b000000,12,12,9);self.load64(12,12,0);
        self.add_imm(16,31,OUTPUT+24);self.add_imm(17,16,code_len.div_ceil(64)*8);self.mov(11,31);
        let words=self.words.len();self.load64(9,16,0);self.cmp(9,31);
        let empty=self.words.len();self.emit(0x54000000);
        let bits=self.words.len();
        self.emit(0xdac00000|(9<<5)|10); // rbit x10,x9
        self.emit(0xdac01000|(10<<5)|10); // clz x10,x10
        self.three(0x8b000000,14,11,10);
        self.emit(0x8b000000|(14<<16)|(3<<10)|(12<<5)|14); // add x14,x12,x14,lsl #3
        self.load64(13,14,0);self.add_imm(13,13,1);self.store64(13,14,0);
        self.sub_imm(15,9,1);self.three(0x8a000000,9,9,15);self.cmp(9,31);
        let more=self.words.len();self.emit(0x54000001);self.patch_conditional(more,bits)?;
        let next=self.words.len();self.patch_conditional(empty,next)?;
        self.add_imm(16,16,8);self.add_imm(11,11,64);self.cmp(16,17);
        let more=self.words.len();self.emit(0x54000003);self.patch_conditional(more,words)?;
        Ok(())
    }
}

#[cfg(all(test,target_arch="aarch64",target_os="macos"))]
mod tests;
