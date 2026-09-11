use super::*;
use crate::{Engine, Limits, Memory, Slot, VERSION, execute_profiled, execute_with_engine};

const LIVE: u128 = 0xfedc_ba98_7654_3210_0123_4567_89ab_cdef;

fn program(size: usize, heap: bool, alias: bool) -> Program {
    Program {
        version: VERSION, target: "aarch64-apple-darwin".into(), entry: 0,
        data: vec![0;64], statics: if heap { vec![0;16] } else { vec![] }, thread_locals: vec![],
        functions: vec![Function {
            name: "medium_copy".into(), frame_size: 512, frame_align: 16,
            registers: 6, args: vec![], result: Slot {offset:0,size:16},
            code: vec![
                Op::Imm {dst:2,value:LIVE},
                Op::Copy {dst:if alias {0} else {1},src:0,size},
                Op::Imm {dst:3,value:19},
                // This unsupported operation keeps the full-width value live
                // across the native exit. The direct probe stops before it.
                Op::Unary {dst:4,src:2,bits:128,op:Unary::CountOnes},
                Op::Return,
            ],
        }],
    }
}

fn memory() -> Memory {
    let mut heap=crate::heap::Heap::default();
    heap.bytes=(0..1024).map(|i|(i*71+19) as u8).collect();
    Memory {bytes:(0..1024).map(|i|(i*43+7) as u8).collect(),heap,
        limit:4096,readonly_end:64,peak:2048,auxiliary_bytes:0}
}

fn probe(jit: &Jit<'_>, m: &mut Memory, src: usize, dst: usize, profiled: bool) -> Result<([u128;6], [u64;5]), String> {
    let mut registers=[src as u128,dst as u128,0,0,0,LIVE];
    let mut hits=[0;5];
    let (next,steps)=unsafe {jit.run(jit.blocks[0][0].unwrap(),5,3,
        if profiled {hits.as_mut_ptr()} else {std::ptr::null_mut()},
        registers.as_mut_ptr(),64,m.bytes.as_mut_ptr(),m.bytes.len(),m.readonly_end,
        m.heap.bytes.as_mut_ptr(),m.heap.bytes.len())}?;
    assert_eq!((next,steps),(3,3));
    assert_eq!(registers[2],LIVE);assert_eq!(registers[5],LIVE);
    assert_eq!(hits,[u64::from(profiled),0,0,0,0]);
    Ok((registers,hits))
}

#[test]
fn native_medium_copies_match_every_length_alignment_arena_and_overlap_direction() {
    for size in 33..=128 {
        for heap in [false,true] {
            let p=program(size,heap,false);crate::validate(&p).unwrap();
            for profiled in [false,true] {
                let mut jit = Jit::new(&p, profiled, MAX_CODE_BYTES).unwrap();
                jit.ensure_function(0).unwrap();
                assert_eq!(jit.blocks[0][0].unwrap().end,3);
                for src_heap in [false,true].into_iter().filter(|h|heap||!*h) {
                    for dst_heap in [false,true].into_iter().filter(|h|heap||!*h) {
                        for alignment in 0..16 {
                            let source=256+alignment;
                            // Include overlap by one byte and by every vector
                            // boundary, identical addresses and disjoint ranges.
                            for delta in [-129,-128,-127,-33,-32,-31,-17,-16,-15,-8,-1,0,1,8,15,16,17,31,32,33,127,128,129] {
                                let dest=(source as isize+delta) as usize;
                                let src=source+if src_heap {crate::heap::TAG} else {0};
                                let dst=dest+if dst_heap {crate::heap::TAG} else {0};
                                let mut expected=memory();expected.copy(src,dst,size).unwrap();
                                let mut actual=memory();probe(&jit,&mut actual,src,dst,profiled).unwrap();
                                assert_eq!(actual.bytes,expected.bytes,"stack size={size} src={src} dst={dst}");
                                assert_eq!(actual.heap.bytes,expected.heap.bytes,"heap size={size} src={src} dst={dst}");
                            }
                        }
                    }
                }
                // Readonly sources are valid; end-exact destination ranges are valid.
                for (src,dst) in [(1,1024-size),(64,1024-size)] {
                    let mut expected=memory();expected.copy(src,dst,size).unwrap();
                    let mut actual=memory();probe(&jit,&mut actual,src,dst,profiled).unwrap();
                    assert_eq!(actual.bytes,expected.bytes);assert_eq!(actual.heap.bytes,expected.heap.bytes);
                }
            }
        }
    }
}

#[test]
fn native_medium_copy_accepts_the_same_address_register() {
    for size in 33..=128 {
        let p=program(size,true,true);let mut jit = Jit::new(&p, false, MAX_CODE_BYTES).unwrap();
                jit.ensure_function(0).unwrap();
        for src in [64,257,1024-size,crate::heap::TAG+1,crate::heap::TAG+257] {
            let mut m=memory();let stack=m.bytes.clone();let heap=m.heap.bytes.clone();
            probe(&jit,&mut m,src,0,false).unwrap();
            assert_eq!(m.bytes,stack);assert_eq!(m.heap.bytes,heap);
        }
    }
}

#[test]
fn native_medium_copy_validates_both_complete_ranges_before_any_write() {
    for size in 33..=128 {
        for heap in [false,true] {
            let p=program(size,heap,false);let mut jit = Jit::new(&p, false, MAX_CODE_BYTES).unwrap();
                jit.ensure_function(0).unwrap();
            let mut bad=vec![0,1024-size+1,1024,1025,usize::MAX];
            if heap {bad.extend([crate::heap::TAG,crate::heap::TAG+1024-size+1,crate::heap::TAG+1024]);}
            for invalid in bad {
                for (src,dst) in [(invalid,256),(256,invalid)] {
                    let mut m=memory();let stack=m.bytes.clone();let heap=m.heap.bytes.clone();
                    assert!(m.copy(src,dst,size).is_err());
                    assert_eq!(probe(&jit,&mut m,src,dst,false).unwrap_err(),"JIT guest memory access failed");
                    assert_eq!(m.bytes,stack);assert_eq!(m.heap.bytes,heap);
                }
            }
            for dst in [1,32,63] {
                let mut m=memory();let stack=m.bytes.clone();let heap=m.heap.bytes.clone();
                assert_eq!(probe(&jit,&mut m,256,dst,false).unwrap_err(),"JIT guest memory access failed");
                assert_eq!(m.bytes,stack);assert_eq!(m.heap.bytes,heap);
            }
        }
    }
}

#[test]
fn native_medium_copies_preserve_exact_budgets_and_larger_copy_fallback() {
    for size in [0,1,16,17,31,32,33,47,48,63,64,65,79,80,81,95,96,111,112,127,128,129,256] {
        let mut p=program(size,false,false);
        p.functions[0].code=vec![
            Op::Local {dst:0,offset:0},Op::Local {dst:1,offset:256},
            Op::Copy {src:0,dst:1,size},Op::Jump {target:4},Op::Imm {dst:2,value:LIVE},
            Op::Local {dst:3,offset:0},Op::Store {address:3,src:2,size:16},Op::Return,
        ];
        for budget in 0..=9 {
            for engine in [Engine::Interpreter,Engine::Jit] {
                let limits=||Limits {instructions:budget,..Limits::default()};
                let normal=execute_with_engine(&p,&[],limits(),engine);
                let observed=execute_profiled(&p,&[],limits(),engine);
                if budget<8 {
                    assert_eq!(normal.unwrap_err(),"interpreter instruction limit exceeded");
                    assert_eq!(observed.unwrap_err(),"interpreter instruction limit exceeded");
                } else {
                    let normal=normal.unwrap();let (observed,profile)=observed.unwrap();
                    assert_eq!(normal.value,LIVE);assert_eq!(observed.value,LIVE);
                    assert_eq!(normal.instructions,8);assert_eq!(observed.instructions,8);
                    assert_eq!(normal.jit_instructions,observed.jit_instructions);
                    if engine==Engine::Jit {
                        assert_eq!(profile.functions[0].interpreted[2],u64::from(size>128));
                        if size<=128 {assert_eq!(normal.jit_entries,1);assert_eq!(normal.jit_instructions,7);}
                    }
                }
            }
        }
    }
}
