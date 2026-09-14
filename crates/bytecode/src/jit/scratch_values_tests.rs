use super::*;
use crate::{Engine, Function, Limits, Op, Program, Slot, execute_profiled, execute_with_engine};
use super::super::Jit;

#[test]
fn scratch_memory_state_bounds_aliases_and_disabled_mode() {
    let mut state=State::default();
    for offset in (0..256).step_by(8) {state.capture(Some(offset),8);}
    assert_eq!(state.len,16);assert!(!state.contains(Some(0),8));assert!(state.contains(Some(248),8));
    assert!(!state.contains(Some(248),4));assert!(!state.contains(None,8));
    state.invalidate(Some(239),2);assert!(!state.contains(Some(232),8));assert!(!state.contains(Some(240),8));
    assert!(state.contains(Some(248),8));state.invalidate(None,0);assert!(state.contains(Some(248),8));
    state.invalidate(None,1);assert_eq!(state.len,0);
    state.capture(Some(usize::MAX),8);assert_eq!(state.len,0);
    let mut state=State::new(false);state.capture(Some(8),8);assert!(!state.contains(Some(8),8));
}

#[test]
fn scratch_memory_classifier_rejects_all_clobbers_and_control_transfers() {
    for r in 0..32 {
        for op in [0x91000400,0xd2800000,0xaa0003e0,0xd340fc00,0x8b010000,
                   0xf9400000,0xb9800000,0x39c00000] {
            let mut state=State::default();state.capture(Some(8),8);state.word(op|r);
            assert_eq!(state.contains(Some(8),8),r!=9,"{op:x} r{r}");
        }
        assert!(preserves_x9(0xf9000000|r));
    }
    for word in [0x54000000,0x14000000,0x94000000,0xd61f0200,0xd65f03c0,
        0,0xffffffff,0x38401569,0x38001529,0xa8c13569,0xa8813520,0xa940256a] {
        let mut state=State::default();state.capture(Some(8),8);state.word(word);
        assert!(!state.contains(Some(8),8),"{word:x}");
    }
    assert!(preserves_x9(0xa9007d69));assert!(preserves_x9(0xa940296b));
}

fn program(code:Vec<Op>)->Program {
    Program{version:crate::VERSION,target:"aarch64-apple-darwin".into(),entry:0,
        data:vec![0;64],statics:vec![],thread_locals:vec![],functions:vec![Function {
        name:"scratch memory differential".into(),frame_size:256,frame_align:16,registers:12,
        args:vec![Slot{offset:16,size:16}],result:Slot{offset:0,size:16},code}]}
}

fn check(p:&Program,args:&[u128],max:u64) {
    crate::validate(p).unwrap();
    for budget in 0..=max {for capacity in [0,super::super::MAX_CODE_BYTES] {for persistent in [false,true] {for resumable in [false,true] {
        let limits=||Limits{instructions:budget,jit_code_bytes:capacity,jit_persistent_registers:persistent,
            jit_resumable_calls:resumable,..Limits::default()};
        let expected=execute_profiled(p,args,limits(),Engine::Interpreter);
        let plain=execute_with_engine(p,args,limits(),Engine::Jit);
        let profiled=execute_profiled(p,args,limits(),Engine::Jit);
        match expected {
            Err(error)=> {
                for actual in [plain.unwrap_err(),profiled.unwrap_err()] {
                    let memory=matches!(error.as_str(),"invalid guest memory access"|"write to read-only guest memory");
                    assert!(actual==error || (capacity!=0 && memory && actual=="JIT guest memory access failed"),
                        "budget {budget}: {actual:?} != {error:?}");
                }
            },
            Ok((expected,ep))=> {
                let plain=plain.unwrap();let (observed,op)=profiled.unwrap();
                for actual in [plain,observed] {
                    assert_eq!((actual.value,actual.instructions,actual.peak_memory),
                        (expected.value,expected.instructions,expected.peak_memory));
                }
                for (actual,expected) in op.functions.iter().zip(ep.functions) {
                    let mut logical=actual.interpreted.clone();
                    for (pc,&hits) in actual.jit_blocks.iter().enumerate() {
                        if hits!=0 {for n in &mut logical[pc..actual.jit_block_ends[pc]] {*n+=hits;}}
                    }
                    assert_eq!(logical,expected.interpreted);
                }
            }
        }
    }}}}
}

fn chain()->Vec<Op> {
    vec![Op::Local{dst:0,offset:16},Op::Local{dst:1,offset:64},
        Op::Copy{dst:1,src:0,size:8},Op::Local{dst:0,offset:80},Op::Copy{dst:0,src:1,size:8},
        Op::Local{dst:1,offset:96},Op::Copy{dst:1,src:0,size:8},Op::Load{dst:2,address:1,size:8}]
}
fn finish(code:&mut Vec<Op>) {
    code.extend([Op::Local{dst:3,offset:0},Op::Store{address:3,src:2,size:16},Op::Return]);
}

#[test]
fn scratch_memory_removes_chained_copy_and_load_words_with_exact_profiles() {
    let mut code=chain();finish(&mut code);let p=program(code);
    for profiled in [false,true] {
        let mut old=Jit::new_resumable(&p,profiled,super::super::MAX_CODE_BYTES,true).unwrap();
        old.scratch_values_enabled=false;
        let new=Jit::new_resumable(&p,profiled,super::super::MAX_CODE_BYTES,true).unwrap();
        let a=old.emit_function_inner(&p.functions[0],super::super::MAX_CODE_BYTES/4,0,None).unwrap().unwrap();
        let b=new.emit_function_inner(&p.functions[0],super::super::MAX_CODE_BYTES/4,0,None).unwrap().unwrap();
        assert_eq!(a.words.len()-b.words.len(),3);assert_eq!(a.operations,b.operations);
        assert_eq!(a.assertions,b.assertions);
    }
    for value in [0,0xfedc_ba98_7654_3210_0123_4567_89ab_cdef,u128::MAX] {
        check(&p,&[value],16);
    }
}

#[test]
fn scratch_memory_retains_partial_aliases_clobbers_faults_and_branch_boundaries() {
    for offset in [64,65,71,72,80,95,96,97,103,104] {for size in [0,1,2,4,8,16] {
        let mut code=chain();
        code.extend([Op::Local{dst:4,offset},Op::Imm{dst:5,value:u128::MAX},
            Op::Store{address:4,src:5,size},Op::Load{dst:2,address:1,size:8}]);
        finish(&mut code);check(&program(code),&[0xabcdef],20);
    }}
    for fault in [false,true] {for branch in [false,true] {
        let mut code=chain();
        // Runtime pointer from guest argument: never promoted from its value.
        code.extend([Op::Local{dst:4,offset:16},Op::Load{dst:5,address:4,size:8},
            Op::Imm{dst:6,value:77},Op::Store{address:5,src:6,size:8}]);
        if branch {let next=code.len()+1;code.push(Op::Jump{target:next});}
        code.push(Op::Load{dst:2,address:1,size:8});finish(&mut code);
        check(&program(code),&[if fault {u64::MAX as u128} else {64+96}],24);
    }}
}
