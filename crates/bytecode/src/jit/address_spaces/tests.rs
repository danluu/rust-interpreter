use super::*;

#[test]
fn branch_arena_selector_encodes_both_high_bits_and_bounded_local_jumps() {
    for address in [9, 10, 11, 12] {
        for write in [false, true] {
            let mut a = Assembler::default();
            a.select_fixed_address_space(address, write);
            assert_eq!(a.words.len(), if write { 11 } else { 9 });
            assert_eq!(a.words[0], 0xd37efc0d | (address << 5));
            assert_eq!(a.words[1], if write { 0xb40000ed } else { 0xb40000cd });
            assert_eq!(a.words[2], 0xd2e8000e);
            assert_eq!(a.words[3], 0xcb0e0000 | (address << 5) | address);
            assert_eq!(a.words[if write { 7 } else { 6 }], if write { 0x14000004 } else { 0x14000003 });
            assert!(a.failures.is_empty() && a.links.is_empty());
        }
    }
}

#[test]
#[cfg(all(target_arch = "aarch64", target_os = "macos"))]
fn branch_arena_selector_matches_unsigned_reference_and_preserves_live_inputs() {
    let tag = crate::HEAP_POINTER_TAG;
    let mut addresses = vec![0, 1, 63, 64, 127, 128, 129, tag-1, tag, tag+1,
        tag+95, tag+96, tag+97, tag*2-1, tag*2, tag*2+1, tag*3-1, tag*3, tag*3+1, u64::MAX];
    let mut state = 0x7359_a215_38f7_9261u64;
    for _ in 0..256 {
        state ^= state << 13; state ^= state >> 7; state ^= state << 17;
        addresses.push(state);
    }
    let mut linear = [0u8;128]; let mut heap = [0u8;96];
    let mut code = platform::Code::reserve(4096).unwrap();
    for address in [9, 10, 11, 12] { for write in [false, true] { for candidate in [false, true] {
        let mut a = Assembler { branch_address_spaces: candidate, ..Assembler::default() };
        a.mov(8,6); a.mov(7,5); // external ABI heap arguments -> internal arena registers
        a.imm(5,0x5555); a.imm(6,0x6666);
        for reg in 9..=12 { a.imm(reg,0x1000+u64::from(reg)); }
        a.mov(address,1);
        a.select_fixed_address_space(address,write);
        // The only stores use a live host output allocation. Arbitrary guest
        // addresses are arithmetic inputs only; none are dereferenced here.
        let saved = [address,17,15,14,5,6,9,10,11,12,1,2,3,4,7,8];
        for (slot,reg) in saved.into_iter().enumerate() {
            a.emit(0xf9000000 | ((slot as u32) << 10) | reg); // str xReg,[x0,#slot*8]
        }
        a.mov(0,31); a.emit(0xd65f03c0);
        let offset = code.append(&a.words).unwrap();
        for &input in &addresses {
            let mut output = [0u128;8];
            unsafe { assert_eq!(code.call(offset,output.as_mut_ptr(),input as usize,linear.as_mut_ptr(),
                linear.len(),64,heap.as_mut_ptr(),heap.len(),std::ptr::null_mut()),0); }
            let words: Vec<u64> = output.into_iter().flat_map(|v|[v as u64,(v>>64) as u64]).collect();
            let is_heap = input >= tag;
            let relative = if is_heap {input-tag} else {input};
            let expected = [relative,if is_heap {heap.as_ptr() as u64} else {linear.as_ptr() as u64},
                if is_heap {96} else {128},if is_heap {0} else {64},0x5555,0x6666,
                if address==9 {relative} else {0x1009},if address==10 {relative} else {0x100a},
                if address==11 {relative} else {0x100b},if address==12 {relative} else {0x100c},
                input,linear.as_ptr() as u64,128,64,heap.as_ptr() as u64,96];
            for i in 0..16 {
                if i==3 && !write { continue; } // reads do not consume readonly scratch
                assert_eq!(words[i],expected[i],"input={input:#x} reg={address} write={write} candidate={candidate} output={i}");
            }
        }
    }}}
}

#[test]
fn branch_arena_scalar_accesses_preserve_bytes_faults_and_address_truncation() {
    use crate::{Memory, Slot, VERSION};
    const VALUE: u128 = 0xfedc_ba98_7654_3210_0123_4567_89ab_cdef;
    let memory = || {
        let mut heap = crate::heap::Heap::default();
        heap.bytes = (0..128).map(|i|(i*71+19) as u8).collect();
        Memory {bytes:(0..128).map(|i|(i*43+7) as u8).collect(),heap,
            limit:4096,readonly_end:64,peak:256,auxiliary_bytes:0}
    };
    for size in 0usize..=16 { for heap in [false,true] { for write in [false,true] {
        let p = Program {version:VERSION,target:"aarch64-apple-darwin".into(),entry:0,
            data:vec![0;64],statics:if heap {vec![0;16]} else {vec![]},thread_locals:vec![],
            functions:vec![Function {name:"fixed scalar bounds".into(),frame_size:64,frame_align:16,
                registers:5,args:vec![],result:Slot {offset:0,size:0},code:vec![
                    if write {Op::Store {address:0,src:1,size:size as u8}} else {Op::Load {dst:1,address:0,size:size as u8}},
                    Op::Imm {dst:2,value:19},Op::Jump {target:3},
                    Op::Unary {dst:3,src:1,bits:128,op:Unary::CountOnes},Op::Return]}]};
        crate::validate(&p).unwrap();
        let tag=crate::heap::TAG;
        let mut addresses=vec![0,1,63,64,65,128-size,129-size,128,129,usize::MAX];
        if heap {addresses.extend([tag-1,tag,tag+1,tag+128-size,tag+129-size,
            tag+128,tag*2-1,tag*2,tag*2+1,tag*3,tag*3+64]);}
        for profiled in [false,true] {
            let mut jit=Jit::new(&p,profiled,MAX_CODE_BYTES).unwrap();jit.ensure_function(0).unwrap();
            for address in &addresses { for high in [0,VALUE<<64] {
                let mut expected=memory();
                let reference=if write {expected.store(*address,size,VALUE).map(|_|VALUE)}
                    else {expected.load(*address,size)};
                let mut actual=memory();let mut registers=[high|*address as u128,VALUE,0,0,VALUE];
                let mut hits=[0u64;5];
                let result=unsafe {jit.run(jit.blocks[0][0].unwrap(),5,3,
                    if profiled {hits.as_mut_ptr()} else {std::ptr::null_mut()},
                    registers.as_mut_ptr(),64,actual.bytes.as_mut_ptr(),actual.bytes.len(),64,
                    actual.heap.bytes.as_mut_ptr(),actual.heap.bytes.len())};
                assert_eq!(result.is_ok(),reference.is_ok(),"size={size} heap={heap} write={write} address={address}");
                match reference {
                    Ok(value)=>{assert_eq!(result.unwrap(),(3,3));assert_eq!(registers[1],value);
                        assert_eq!(hits,[u64::from(profiled),0,0,0,0]);}
                    Err(_)=>assert_eq!(result.unwrap_err(),"JIT guest memory access failed"),
                }
                assert_eq!(registers[4],VALUE);
                assert_eq!(&*actual.bytes,&*expected.bytes);assert_eq!(actual.heap.bytes,expected.heap.bytes);
            }}
        }
    }}}
}
