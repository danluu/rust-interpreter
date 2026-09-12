use super::*;

#[test]
fn call_cost_covers_both_extents_and_rejects_host_overflow() {
    let mut f = function(vec![Op::Return]);
    for size in [0usize, 1, 17, 256, usize::MAX / 2, usize::MAX] {
        for align in [1usize, 16, 4096, 1usize << 63] {
            for registers in [0usize, 1, 2049, usize::MAX / 16, usize::MAX] {
                f.frame_size = size; f.frame_align = align; f.registers = registers;
                let expected = size.max(1) as u128 + align as u128 - 1 + 16 * registers as u128;
                assert_eq!(call_capacity_cost(&f), usize::try_from(expected).ok());
            }
        }
    }
    f.frame_align = 0;
    assert_eq!(call_capacity_cost(&f), None);
}

#[test]
fn credit_remains_conservative_across_mixed_calls_and_retained_padding() {
    // Independent wide-integer model; no guest addresses are dereferenced.
    let mut f = function(vec![Op::Return]);
    for seed in 0..32u128 {
        let (mut memory, mut registers) = (17 + seed, 8u128);
        let (end, slots, budget) = (1_000_000u128, 30_000u128, 1_000_000u128);
        let mut credit = 0u128;
        let mut stack = vec![];
        for step in 0..600u128 {
            let slack = |m, r| (end-m).min(16*(slots-r)).min(budget-m-16*r);
            assert!(credit <= slack(memory, registers));
            if step % 3 == 2 && !stack.is_empty() {
                // Return retains the callee's actual aligned base, not the
                // old caller end. Credit is intentionally not refunded.
                (memory, registers) = stack.pop().unwrap();
            } else {
                f.frame_align = 1 << ((step + seed) % 7);
                f.frame_size = ((step * 17 + seed) % 257) as usize;
                f.registers = ((step * 13 + seed) % 65) as usize;
                let cost = call_capacity_cost(&f).unwrap() as u128;
                let base = memory.div_ceil(f.frame_align as u128) * f.frame_align as u128;
                let next = base + f.frame_size.max(1) as u128;
                let regs = registers + f.registers as u128;
                assert!(next <= end && regs <= slots && next + 16*regs <= budget);
                credit = if credit >= cost { credit-cost } else { slack(next, regs) };
                stack.push((base, registers));
                (memory, registers) = (next, regs);
            }
            assert!(credit <= slack(memory, registers));
        }
    }
}

#[test]
fn emitted_capacity_checks_match_independent_bounds_and_exact_credit() {
    let mut code = platform::Code::reserve(256 * 1024).unwrap();
    for size in [0usize, 1, 17, 257, 8192] {
        for align in [1usize, 16, 4096] {
            for count in [0usize, 1, 9, 2050] {
                let mut f = function(vec![Op::Return]);
                f.frame_size=size; f.frame_align=align; f.registers=count;
                let mut a = Assembler::default();
                a.resumable_save_host(false);
                a.mov(19,7);
                a.load64(CALL_CREDIT_REGISTER,19,state::CALLS); // scalar probe seed
                a.imm(16,0x1357); a.imm(22,0x2468);
                let mut declines=vec![];
                a.resumable_call_capacity(&f,&mut declines).unwrap();
                for (reg,offset) in [(CALL_CREDIT_REGISTER,0),(21,8),(16,16),(22,24)] {
                    a.store64(reg,0,offset);
                }
                a.mov(0,31); a.resumable_save_host(true); a.emit(0xd65f03c0);
                let failed=a.words.len();
                a.imm(0,1); a.resumable_save_host(true); a.emit(0xd65f03c0);
                for at in declines {a.patch_conditional(at,failed).unwrap();}
                assert!(a.words.iter().all(|w| w & 0xfc000000 != 0x94000000
                    && w & 0xfffffc1f != 0xd63f0000), "capacity probe cannot link-call");
                let entry=code.append(&a.words).unwrap();
                for old_memory in [17usize,64,4095] {
                    let old_registers=8usize;
                    let base=old_memory.div_ceil(align)*align;
                    let next=base+size.max(1);
                    let need=next-old_memory;
                    let register_bytes=count*16;
                    for extra_memory in [0,need.saturating_sub(1),need,need+4096] {
                        for extra_registers in [0,count.saturating_sub(1),count,count+256] {
                            for extra_work in [0,(need+register_bytes).saturating_sub(1),need+register_bytes,need+register_bytes+4096] {
                                let end=old_memory+extra_memory;
                                let slots=old_registers+extra_registers;
                                let budget=old_memory+16*old_registers+extra_work;
                                let slack=extra_memory.min(16*extra_registers).min(extra_work);
                                let fits=need<=extra_memory && count<=extra_registers && need+register_bytes<=extra_work;
                                for seed in [0,slack/2,slack] {
                                    let mut cursor=ResumeCursor {
                                        state:State {remaining:0,profile_hits:std::ptr::null_mut(),memory_len:old_memory,
                                            peak_linear:old_memory,register_len:old_registers,frame_len:1,calls:seed as u64,returns:0},
                                        frames:std::ptr::null_mut(),registers:std::ptr::null_mut(),entries:std::ptr::null(),
                                        profiles:std::ptr::null(),memory_end:end,register_end:slots,frame_end:1,working_budget:budget,
                                    };
                                    let mut output=[u128::MAX;2];
                                    // SAFETY: this scalar-only owned probe reads the live cursor
                                    // and writes only output. It never accesses guest buffers or
                                    // treats the tested capacity values as host address ranges.
                                    let status=unsafe {code.call(entry,output.as_mut_ptr(),0,std::ptr::null_mut(),old_memory,
                                        0,std::ptr::null_mut(),0,std::ptr::addr_of_mut!(cursor).cast())};
                                    assert_eq!(status,usize::from(!fits) as u64);
                                    if fits {
                                        let cost=call_capacity_cost(&f).unwrap();
                                        let expected=if seed>=cost {seed-cost} else {
                                            (end-next).min(16*(slots-old_registers-count)).min(budget-next-16*(old_registers+count))
                                        };
                                        assert_eq!(output,[(base as u128)<<64|expected as u128,0x2468u128<<64|0x1357]);
                                    } else { assert_eq!(output,[u128::MAX;2]); }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

#[test]
fn repeated_real_calls_refresh_credit_and_preserve_small_limits() {
    let root=function(vec![Op::Local {dst:0,offset:0},Op::Imm {dst:1,value:4000},Op::Imm {dst:2,value:1},
        Op::Call {function:1,args:vec![],destination:0},binary(1,Binary::Sub,1,2),
        Op::Switch {value:1,cases:vec![(0,6)],otherwise:3},Op::Return]);
    let mut child=function(vec![Op::Return]);
    child.frame_size=257; child.frame_align=64;
    let p=program(vec![root,child]);
    crate::validate(&p).unwrap();
    let reference=execute_with_engine(&p,&[],Limits::default(),Engine::Interpreter).unwrap();
    for bytes in [64usize,512,1024,2048,64*1024*1024] {
        for budget in [0,1,3,4,99,reference.instructions-1,reference.instructions,reference.instructions+1] {
            let expected=execute_with_engine(&p,&[],Limits {memory:bytes,instructions:budget,..Limits::default()},Engine::Interpreter);
            for persistent in [false,true] {
                equal_result(execute_with_engine(&p,&[],Limits {memory:bytes,instructions:budget,
                    jit_resumable_calls:true,jit_persistent_registers:persistent,..Limits::default()},Engine::Jit),&expected);
            }
        }
    }
}
