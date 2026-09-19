use super::*;
use crate::{Engine, Limits, Slot, execute_profiled, execute_with_engine};

const WIDE: u128 = 0xfedc_ba98_7654_3210_0123_4567_89ab_cdef;

pub(super) fn program(code: Vec<Op>, registers: usize, args: usize) -> Program {
    Program { version:crate::VERSION,target:"aarch64-apple-darwin".into(),entry:0,
        data:vec![0;16],statics:vec![],thread_locals:vec![],
        functions:vec![Function {name:"successor flush".into(),frame_size:256,frame_align:16,registers,
            args:(0..args).map(|i|Slot {offset:16+i*16,size:16}).collect(),
            result:Slot {offset:0,size:16},code}] }
}

pub(super) fn compare(p: &Program, args: &[u128], expected: u128) {
    crate::validate(p).unwrap();
    let reference=execute_with_engine(p,args,Limits::default(),Engine::Interpreter).unwrap();
    assert_eq!(reference.value,expected);
    for budget in 0..=reference.instructions {
        let reference=execute_profiled(p,args,Limits {instructions:budget,..Limits::default()},Engine::Interpreter);
        for persistent in [false,true] {for capacity in [0,MAX_CODE_BYTES] {
            for (resumable,tree,stubs) in [(false,false,false),(true,false,false),(false,true,false),(false,true,true)] {
                let limits=||Limits {instructions:budget,jit_code_bytes:capacity,
                    jit_persistent_registers:persistent,jit_resumable_calls:resumable,
                    jit_native_calls:tree,jit_native_call_stubs:stubs,..Limits::default()};
                let normal=execute_with_engine(p,args,limits(),Engine::Jit);
                let observed=execute_profiled(p,args,limits(),Engine::Jit);
                match &reference {
                    Err(error)=>{assert_eq!(&normal.unwrap_err(),error);assert_eq!(&observed.unwrap_err(),error);}
                    Ok((r,rp))=>{
                        let normal=normal.unwrap();let (observed,profile)=observed.unwrap();
                        assert_eq!((normal.value,normal.instructions,normal.peak_memory),(r.value,r.instructions,r.peak_memory));
                        assert_eq!((observed.value,observed.instructions),(r.value,r.instructions));
                        for (f,rf) in profile.functions.iter().zip(&rp.functions) {
                            let mut logical=f.interpreted.clone();
                            for (pc,&n) in f.jit_blocks.iter().enumerate() {
                                if n!=0 {for count in &mut logical[pc..f.jit_block_ends[pc]] {*count+=n;}}
                            }
                            for (pc,&n) in f.jit_tree_blocks.iter().enumerate() {
                                if n!=0 {for count in &mut logical[pc..f.jit_tree_block_ends[pc]] {*count+=n;}}
                            }
                            assert_eq!(logical,rf.interpreted);
                        }
                    }
                }
            }
        }}
    }
}

fn emitted(p: &Program, optimized: bool, persistent: bool) -> CompiledFunction<'_> {
    let mut jit=Jit::new_resumable(p,false,MAX_CODE_BYTES,persistent).unwrap();
    jit.omit_dead_exit_spills=optimized;jit.observe_flush=true;
    jit.emit_function_inner(&p.functions[0],MAX_CODE_BYTES/4,0,None).unwrap().unwrap()
}

#[test]
fn successor_flush_omits_dead_wide_branch_spills_and_preserves_selection() {
    for r in [0,2050] {
        let p=program(vec![Op::Local {dst:r,offset:16},Op::Load {dst:r+1,address:r,size:16},
            Op::Switch {value:r+1,cases:vec![(0,3),(1<<64,7),(1<<64,11)],otherwise:11},
            Op::Imm {dst:r+2,value:11},Op::Local {dst:r,offset:0},Op::Store {address:r,src:r+2,size:16},Op::Return,
            Op::Imm {dst:r+2,value:22},Op::Local {dst:r,offset:0},Op::Store {address:r,src:r+2,size:16},Op::Return,
            Op::Imm {dst:r+2,value:WIDE},Op::Local {dst:r,offset:0},Op::Store {address:r,src:r+2,size:16},Op::Return,
        ],r as usize+8,1);
        let a=emitted(&p,false,true);let b=emitted(&p,true,true);
        assert!(b.words.len()<a.words.len());
        assert!(a.flush_spans.iter().any(|s|s.region_start==0 && !s.live_after && !s.tail_consumed));
        assert!(!b.flush_spans.iter().any(|s|s.region_start==0));
        assert_eq!(emitted(&p,false,false).words,emitted(&p,true,false).words);
        for (value,expected) in [(0,11),(1<<64,22),(1,WIDE),(WIDE,WIDE)] {compare(&p,&[value],expected);}
    }
}

#[test]
fn successor_flush_preserves_wide_values_live_through_both_join_edges() {
    let mut code=vec![];
    for i in 0..4 {code.extend([Op::Local {dst:i*2,offset:16+i as usize*16},
        Op::Load {dst:i*2+1,address:i*2,size:16}]);}
    code.extend([Op::Switch {value:1,cases:vec![(0,9)],otherwise:10},Op::Jump {target:11},Op::Jump {target:11},
        Op::Binary {dst:0,overflow:8,op:Binary::Xor,a:1,b:3,bits:128,signed:false},
        Op::Binary {dst:0,overflow:8,op:Binary::Xor,a:0,b:5,bits:128,signed:false},
        Op::Binary {dst:0,overflow:8,op:Binary::Xor,a:0,b:7,bits:128,signed:false},
        Op::Local {dst:2,offset:0},Op::Store {address:2,src:0,size:16},Op::Return]);
    let p=program(code,10,4);
    let a=emitted(&p,false,true);let b=emitted(&p,true,true);
    let before:Vec<_>=a.flush_spans.iter().filter(|s|s.region_start==0).map(|s|(s.register,s.end-s.offset)).collect();
    let after:Vec<_>=b.flush_spans.iter().filter(|s|s.region_start==0).map(|s|(s.register,s.end-s.offset)).collect();
    assert!(!before.is_empty());assert_eq!(before,after);
    assert!(b.flush_spans.iter().filter(|s|s.region_start==0).all(|s|s.live_after));
    for args in [[0,WIDE,!WIDE,1<<127],[1<<64,0,WIDE,u128::MAX]] {
        compare(&p,&args,args.into_iter().fold(0,|a,b|a^b));
    }
}

#[test]
fn successor_flush_keeps_frame_arguments_before_native_and_vm_calls() {
    let mut code=vec![];
    for dst in 0..5 {code.push(Op::Local {dst,offset:16+dst as usize*16});}
    code.extend([Op::Local {dst:5,offset:0},Op::Call {function:1,args:vec![0,1,2,3,4],destination:5},Op::Return]);
    let mut p=program(code,8,5);
    p.functions.push(Function {name:"fifth argument".into(),frame_size:112,frame_align:16,registers:3,
        args:(0..5).map(|i|Slot {offset:16+i*16,size:16}).collect(),result:Slot {offset:0,size:16},
        code:vec![Op::Local {dst:0,offset:80},Op::Load {dst:1,address:0,size:16},
            Op::Local {dst:2,offset:0},Op::Store {address:2,src:1,size:16},Op::Return]});
    let b=emitted(&p,true,true);
    assert!(b.flush_spans.iter().filter(|s|s.region_start==0).count()>=3);
    assert!(b.flush_spans.iter().filter(|s|s.region_start==0).all(|s|s.live_after));
    compare(&p,&[!WIDE,1<<127,1,0,WIDE],WIDE);
}
