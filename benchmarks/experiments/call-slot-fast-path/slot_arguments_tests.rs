use super::*;

fn address_leaf(guarded: bool, reg: Reg, size: usize, hint: Option<usize>) -> Vec<u32> {
    let mut a=Assembler { heap:true,frame_size:64,..Assembler::default() };
    a.mov(7,5);a.mov(8,6);
    if guarded { a.call_argument_address(reg,size,hint).unwrap(); }
    else { a.address(11,reg,size,false); }
    a.mov(0,11);a.emit(0xd65f03c0);
    let failures=std::mem::take(&mut a.failures);let target=a.words.len();
    a.imm(0,Failure::Memory as u64);a.emit(0xd65f03c0);
    for (at,kind) in failures { assert!(matches!(kind,Failure::Memory));a.patch_conditional(at,target).unwrap(); }
    a.words
}

#[test]
fn guarded_address_matches_original_for_arbitrary_entry_registers_and_extents() {
    let mut code=platform::Code::reserve(1024*1024).unwrap();
    let mut memory=vec![0xa5u8;256];let mut heap=vec![0xbdu8;128];
    let mut registers=vec![0u128;4501];
    let addresses=[0,1,8,16,24,72,79,80,128,248,255,256,usize::MAX,
        crate::heap::TAG,crate::heap::TAG+8,crate::heap::TAG+120,crate::heap::TAG+128];
    for reg in [0,4500] {
        for size in [0,1,8,16,32,64,512] {
            for hint in [None,Some(0),Some(8),Some(56),Some(64),Some(usize::MAX)] {
                let old=code.append(&address_leaf(false,reg,size,hint)).unwrap();
                let new=code.append(&address_leaf(true,reg,size,hint)).unwrap();
                for address in addresses {
                    for high in [0,1u128<<127] {
                        registers[reg as usize]=address as u128|high;
                        // SAFETY: both owned leaves only calculate/check addresses;
                        // all host backing is initialized, exclusive and stable.
                        let invoke=|entry| unsafe { code.call(entry,registers.as_mut_ptr(),16,
                            memory.as_mut_ptr(),memory.len(),16,heap.as_mut_ptr(),heap.len(),std::ptr::null_mut()) };
                        let mut invoke=invoke;
                        assert_eq!(invoke(new),invoke(old),"reg={reg} size={size} hint={hint:?} address={address:x}");
                    }
                }
            }
        }
    }
    assert!(memory.iter().all(|&b| b==0xa5));assert!(heap.iter().all(|&b| b==0xbd));
}

#[derive(Debug,PartialEq,Eq)]
struct Snapshot {
    status:usize, remaining:u64, extents:[usize;4], calls:u64, returns:u64,
    memory:Vec<u8>, heap:Vec<u8>, registers:Vec<u128>, frames:Vec<Frame>, hits:Vec<Vec<u64>>,
}

fn direct_entry(p:&Program,jit:&Jit<'_>,values:[u128;3],budget:u64,frame_end:usize) -> Snapshot {
    let n=p.functions[0].registers;
    let mut memory:Vec<_>=(0..288).map(|i|(i%239) as u8).collect();
    let mut heap:Vec<_>=(0..128).map(|i|(i+73) as u8).collect();
    let mut registers=vec![0xeeu128;n+32];
    let first=n-3;
    registers[first..first+3].copy_from_slice(&values);
    let root=Frame{function:0,pc:3,base:16,register_base:0,return_address:0,tls_callback:false};
    let canary=Frame{function:987,pc:456,base:123,register_base:789,return_address:321,tls_callback:true};
    let mut frames=vec![root,Frame::default(),Frame::default(),canary];
    let mut hits:Vec<_>=p.functions.iter().map(|f|vec![0u64;f.code.len()]).collect();
    let profiles:Vec<_>=hits.iter_mut().map(|r|r.as_mut_ptr()).collect();
    let mut cursor=ResumeCursor { state:State{remaining:budget,profile_hits:profiles[0],memory_len:48,
        peak_linear:48,register_len:n,frame_len:1,calls:0,returns:0},
        frames:frames.as_mut_ptr(),registers:registers.as_mut_ptr(),
        entries:jit.resumable.as_ref().unwrap().pointers.as_ptr(),profiles:profiles.as_ptr(),
        memory_end:256,register_end:n+16,frame_end,frame_limit:3,working_budget:1024*1024 };
    let args=[registers.as_mut_ptr() as usize,16,memory.as_mut_ptr() as usize,48,16,
        heap.as_mut_ptr() as usize,heap.len(),std::ptr::addr_of_mut!(cursor) as usize];
    // SAFETY: emitter-owned entry and prepared initialized/canary-backed storage.
    // Values intentionally do not necessarily match the skipped Local prefix.
    let output=unsafe { jit.code.as_ref().unwrap().tree_abi_probe(jit.blocks[0][3].unwrap().offset,args) };
    assert_eq!(&output[1..5],&[0x1357,0x2468,0x3579,0x468a]);
    assert_eq!(&output[7..],&[0x579b,0x68ac,0x79bd,0x8ace,0x9bdf,0xace0]);
    assert_eq!(output[5],output[6]);assert_eq!(output[6]%16,0);
    assert_eq!(frames[3],canary);
    Snapshot { status:output[0],remaining:cursor.state.remaining,
        extents:[cursor.state.memory_len,cursor.state.peak_linear,cursor.state.register_len,cursor.state.frame_len],
        calls:cursor.state.calls,returns:cursor.state.returns,memory,heap,registers,frames,hits }
}

#[test]
fn external_call_guards_preserve_fault_order_partial_copies_and_native_abi() {
    for registers in [8,5000] {
        let r=registers as Reg-3;
        let mut root=function(vec![Op::Local{dst:r,offset:0},Op::Local{dst:r+1,offset:8},
            Op::Local{dst:r+2,offset:16},Op::Call{function:1,args:vec![r,r+1],destination:r+2},Op::Return]);
        root.registers=registers;root.result=Slot{offset:16,size:8};
        let mut child=function(vec![Op::Local{dst:0,offset:0},Op::Load{dst:1,address:0,size:8},
            Op::Local{dst:2,offset:8},Op::Load{dst:3,address:2,size:8},binary(4,Binary::Add,1,3),
            Op::Store{address:0,src:4,size:8},Op::Return]);
        child.args=vec![Slot{offset:0,size:8},Slot{offset:8,size:8}];
        let mut p=program(vec![root,child]);p.statics=vec![0;16];crate::validate(&p).unwrap();
        assert_eq!(super::super::super::call_slots::collect(&p.functions[0],&p)[&3],vec![Some(0),Some(8)]);
        for persistent in [false,true] { for profiled in [false,true] {
            let mut old=Jit::new_resumable(&p,profiled,MAX_CODE_BYTES,persistent).unwrap();
            old.disable_call_slot_hints=true;
            let mut new=Jit::new_resumable(&p,profiled,MAX_CODE_BYTES,persistent).unwrap();
            for jit in [&mut old,&mut new] { jit.ensure_function(0).unwrap();jit.ensure_function(1).unwrap(); }
            for pair in [(16,24),(24,16),(crate::heap::TAG+16,24),(16,crate::heap::TAG+32),
                (16,0),(0,24),(usize::MAX,24),(1,24),(40,48)] {
                for result in [32,0] { for budget in 0..=12 { for frame_end in [1,3] {
                    let high=1u128<<127;
                    let values=[pair.0 as u128|high,pair.1 as u128|high,result as u128|high];
                    assert_eq!(direct_entry(&p,&new,values,budget,frame_end),direct_entry(&p,&old,values,budget,frame_end),
                        "registers={registers} persistent={persistent} profiled={profiled} args={pair:?} result={result} budget={budget} frames={frame_end}");
                } } }
            }
        } }
    }
}

fn check_profiles_at_all_budgets(p: &Program) {
    let total = execute_with_engine(p, &[], Limits::default(), Engine::Interpreter)
        .map(|r| r.instructions).unwrap_or(40);
    for budget in 0..=total + 1 {
        let reference = execute_profiled(p, &[], Limits { instructions: budget, ..Limits::default() }, Engine::Interpreter);
        for persistent in [false, true] {
            let limits = || Limits { instructions: budget, jit_resumable_calls: true,
                jit_persistent_registers: persistent, ..Limits::default() };
            let actual = execute_profiled(p, &[], limits(), Engine::Jit);
            match (actual, &reference) {
                (Ok((a, ap)), Ok((b, bp))) => {
                    assert_eq!((a.value, a.instructions, a.peak_memory), (b.value, b.instructions, b.peak_memory));
                    assert_eq!(logical(&ap), logical(bp));
                    assert_eq!(logical(&ap).iter().flatten().sum::<u64>(), a.instructions);
                    let plain = execute_with_engine(p, &[], limits(), Engine::Jit).unwrap();
                    assert_eq!((plain.value, plain.instructions, plain.peak_memory), (a.value, a.instructions, a.peak_memory));
                    assert_eq!((plain.jit_resumable_calls, plain.jit_resumable_returns),
                               (a.jit_resumable_calls, a.jit_resumable_returns));
                }
                (Err(a), Err(b)) => {
                    // Existing JIT memory-fault wording differs from the
                    // interpreter. Only this exact known pair is equivalent;
                    // instruction limits and every other error must match.
                    if a == "JIT guest memory access failed" {
                        assert_eq!(b, "invalid guest memory access");
                    } else {
                        assert_eq!(a, *b);
                    }
                }
                (a, b) => panic!("budget {budget} persistent={persistent}: {a:?} versus {b:?}"),
            }
        }
    }
}


fn large_copy(invalid_return: bool) -> Program {
    let mut root = function(vec![
        Op::Local { dst: 0, offset: 0 },
        Op::Imm { dst: 1, value: 111 },
        Op::Store { address: 0, src: 1, size: 8 },
        if invalid_return { Op::Imm { dst: 4500, value: 0 } }
        else { Op::Local { dst: 4500, offset: 1024 } },
        Op::Call { function: 1, args: vec![0], destination: 4500 },
        // The first call compiles the callee lazily. The second must exercise
        // native Call argument copying and register zeroing with that code live.
        Op::Call { function: 1, args: vec![0], destination: 4500 },
        Op::Return,
    ]);
    root.frame_size = 2048;
    root.registers = 5000;
    root.result = Slot { offset: 1024, size: 8 };
    let mut child = function(vec![
        Op::Local { dst: 0, offset: 0 },
        Op::Load { dst: 1, address: 0, size: 8 },
        // This read-before-definition forces large entry-register zeroing.
        binary(2, Binary::Add, 1, 5500),
        Op::Store { address: 0, src: 2, size: 8 },
        Op::Imm { dst: 5500, value: 999 }, // dirty the next native entry's storage
        Op::Return,
    ]);
    child.frame_size = 512;
    child.registers = 6000;
    child.args = vec![Slot { offset: 0, size: 512 }];
    child.result = Slot { offset: 0, size: 512 };
    program(vec![root, child])
}


#[test]
fn guarded_calls_preserve_each_budget_through_loops_recursion_and_fallback() {
    for unsupported in [false,true] { check_profiles_at_all_budgets(&looping_program(unsupported)); }
    check_profiles_at_all_budgets(&recursive_program(3));
}

#[test]
fn large_argument_copies_and_return_faults_keep_exact_budget_accounting() {
    for invalid_return in [false,true] { check_profiles_at_all_budgets(&large_copy(invalid_return)); }
}
