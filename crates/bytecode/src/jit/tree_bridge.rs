//! Private metadata for a complete tree entered from a resumable Call.
//! No guest address can name this cursor or the prepared descriptor array.
use super::*;
use crate::frames::{Frame,layout as frame};
use crate::native_continuation::{Capacity,State};
use native_calls::TreeCursor;

/// Exclude every guarded ordinary body and all its ancestors. A bridge must
/// not discard an adopted body optimization or use its VM-returning decline.
/// Region boundaries and work limits are shared with the ordinary emitter.
pub(super) fn plans(program: &Program) -> Vec<Result<trees::Plan, trees::Decline>> {
    let mut plans = trees::analyze(program);
    let mut parents = vec![vec![]; program.functions.len()];
    let mut declined = std::collections::VecDeque::new();
    for (id, f) in program.functions.iter().enumerate() {
        for op in &f.code {
            if let Op::Call { function, .. } = op { parents[*function].push(id); }
        }
        if plans[id].is_err() { continue; }
        let fills = local_fills(f);
        let native = |pc| supported(&f.code[pc]) || fills.contains_key(&pc) || transfers::supported(&f.code[pc]);
        let starts = region_starts(f, &native);
        let mut work = 4_000_000;
        let mut pc = 0;
        while pc < f.code.len() {
            let end = region_end(f, pc, &starts, &native);
            if end > pc && range_groups::runtime_plan(f, pc, end, &mut work).is_some() {
                plans[id] = Err(trees::Decline::UnsupportedOperation);
                declined.push_back(id);
                break;
            }
            pc = end.max(pc + 1);
        }
    }
    while let Some(child) = declined.pop_front() {
        for &parent in &parents[child] {
            if plans[parent].is_ok() {
                plans[parent] = Err(trees::Decline::UnavailableDependency);
                declined.push_back(parent);
            }
        }
    }
    plans
}

#[cfg(all(test, target_arch="aarch64", target_os="macos"))]
#[path="tree_bridge_nested_tests.rs"]
mod nested;

#[repr(C)]
pub(super) struct BridgeCursor {
    pub tree: TreeCursor,
    pub frames: *mut Frame,
    pub registers: *mut u128,
    pub depth: usize,
    pub fault_depth: usize,
    pub fault_register_end: usize,
}

impl BridgeCursor {
    pub(super) fn new(registers: *mut u128, profile_table: *const *mut u64) -> Self {
        Self {
            tree: TreeCursor { base: Cursor { remaining: 0, profile_hits: std::ptr::null_mut() },
                memory_len: 0, peak_linear: 0, return_address: 0, profile_table,
                calls: 0, tree_instructions: 0, regions_ready: 0, stub_calls: 0 },
            frames: std::ptr::null_mut(), registers, depth: 0, fault_depth: 0, fault_register_end: 0,
        }
    }
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
        self.load64(9,19,resumable::BRIDGE+layout::DEPTH);
        self.add_imm(9,9,1);
        self.store64(9,19,resumable::BRIDGE+layout::DEPTH);
    }

    pub(super) fn bridge_leave_tree_frame(&mut self) {
        if self.tree_bridge_frame.is_none() {return;}
        self.load64(9,19,resumable::BRIDGE+layout::DEPTH);
        self.sub_imm(9,9,1);
        self.store64(9,19,resumable::BRIDGE+layout::DEPTH);
    }

    /// Materialize only on terminal failure, while this function's bounded
    /// host frame still contains its original entry pointers and continuation.
    /// Preserve x0 (fault), x1–x8 (guest arenas) and x19–x30 (host/tree state).
    pub(super) fn bridge_fault_frame(&mut self) -> Result<(),EmitError> {
        let Some((function,registers))=self.tree_bridge_frame else {return Ok(());};
        self.load64(9,31,32); // saved function-entry register pointer
        self.load64(10,19,resumable::BRIDGE+layout::REGISTERS);
        self.three(0xcb000000,9,9,10);
        self.emit(0xd340fc00|(4<<16)|(9<<5)|9); // lsr x9,x9,#4: absolute slot base
        self.load64(10,19,resumable::BRIDGE+layout::DEPTH);
        self.sub_imm(11,10,1);
        self.imm(12,frame::SIZE as u64);
        self.three(0x9b007c00,11,11,12);
        self.load64(12,19,resumable::BRIDGE+layout::FRAMES);
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
        self.load64(12,19,resumable::BRIDGE+layout::FAULT_DEPTH);
        self.cmp(12,31);
        let recorded=self.words.len();self.emit(0x54000001); // b.ne already captured
        self.store64(10,19,resumable::BRIDGE+layout::FAULT_DEPTH);
        self.imm(12,registers as u64);
        self.three(0x8b000000,9,9,12);
        self.store64(9,19,resumable::BRIDGE+layout::FAULT_REGISTER_END);
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

    #[test]
    #[cfg(all(target_arch="aarch64",target_os="macos"))]
    fn fault_materialization_uses_saved_entry_pointers_and_preserves_native_abi() {
        let mut a=Assembler::default();
        a.push_pair(19,30,16);a.mov(19,7);
        let call=a.words.len();a.emit(0x94000000);
        a.pop_pair(19,30,16);a.emit(0xd65f03c0);
        let internal=a.words.len();
        a.words[call]|=branch_displacement(call,internal,26,CodegenLimit::Jump).unwrap();
        a.tree_bridge_frame=Some((4,7));
        a.tree_push_frame();
        a.imm(20,456); // this tree function's guest result destination
        a.imm(9,13);a.store64(9,31,layout::HOST_PC);
        // A child's terminal exit may leave x1 naming that child's frame.
        // The descriptor must use this function's saved entry base instead.
        a.imm(1,777);
        a.imm(0,Failure::Memory as u64);
        a.bridge_fault_frame().unwrap();
        a.tree_epilogue();
        let mut code=platform::Code::reserve(4096).unwrap();let entry=code.append(&a.words).unwrap();
        for depth in [1,2,4] {
            for previous_fault in [0,5] {
                let sentinel=Frame {function:99,pc:99,base:99,register_base:99,return_address:99,tls_callback:true};
                let mut frames=vec![sentinel;6];let mut registers=vec![u128::MAX;40];let mut memory=vec![23u8;512];
                let mut cursor=BridgeCursor {
                    tree:TreeCursor {base:Cursor {remaining:1000,profile_hits:std::ptr::null_mut()},
                        memory_len:512,peak_linear:512,return_address:0,profile_table:std::ptr::null(),
                        calls:6,tree_instructions:0,regions_ready:0,stub_calls:0},
                    frames:frames.as_mut_ptr(),registers:registers.as_mut_ptr(),depth,
                    fault_depth:previous_fault,fault_register_end:37,
                };
                let mut cursor=resumable::ResumeCursor::for_tree_probe(cursor);
                // SAFETY: the only descriptor index is depth-1<6. The saved
                // register pointer is aligned and lies in the same live array
                // as the cursor's base. Every host object is distinct, fully
                // initialized and exclusively owned through this exact probe.
                let output=unsafe {code.tree_abi_probe(entry,[registers.as_mut_ptr().add(3) as usize,
                    64,memory.as_mut_ptr() as usize,512,16,0,0,(&mut cursor as *mut resumable::ResumeCursor) as usize])};
                let cursor=cursor.into_tree_probe();
                assert_eq!(output[0],Failure::Memory as usize);
                assert_eq!(&output[1..5],&[0x1357,0x2468,0x3579,0x468a]);
                assert_eq!(output[5],output[6]);
                assert_eq!(&output[7..],&[0x579b,0x68ac,0x79bd,0x8ace,0x9bdf,0xace0]);
                assert_eq!(frames[depth-1],Frame {function:4,pc:13,base:64,register_base:3,
                    return_address:456,tls_callback:false});
                assert!(frames.iter().enumerate().all(|(i,f)|i==depth-1 || *f==sentinel));
                assert_eq!(cursor.depth,depth-1);
                assert_eq!(cursor.fault_depth,if previous_fault==0 {depth} else {5});
                assert_eq!(cursor.fault_register_end,if previous_fault==0 {10} else {37});
                assert_eq!(cursor.tree.base.remaining,1000);assert_eq!(cursor.tree.calls,6);
                assert_eq!(cursor.tree.memory_len,512);assert_eq!(cursor.tree.peak_linear,512);
                assert_eq!(registers,vec![u128::MAX;40]);assert_eq!(memory,vec![23u8;512]);
            }
        }
    }
}
