use super::super::*;
use crate::{Engine, Limits, Slot, execute_profiled, execute_with_engine};

fn program(code: Vec<Op>, registers: usize, args: usize) -> Program {
    Program { version:crate::VERSION,target:"aarch64-apple-darwin".into(),entry:0,
        data:vec![0;16],statics:vec![],thread_locals:vec![],
        functions:vec![Function {name:"compact switch".into(),frame_size:256,frame_align:16,registers,
            args:(0..args).map(|i|Slot {offset:16+i*16,size:16}).collect(),
            result:Slot {offset:0,size:16},code}] }
}

fn compare(p: &Program, args: &[u128], expected: u128) {
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


fn dispatch(cases:&[u128])->Program {
    let targets=cases.iter().enumerate().map(|(i,&value)|(value,3+i*4)).collect();
    let mut code=vec![Op::Local{dst:0,offset:16},Op::Load{dst:1,address:0,size:16},
        Op::Switch{value:1,cases:targets,otherwise:3+4*cases.len()}];
    for value in (1..=cases.len() as u128).chain([999]) {
        code.extend([Op::Imm{dst:2,value},Op::Local{dst:0,offset:0},
            Op::Store{address:0,src:2,size:16},Op::Return]);
    }
    program(code,8,1)
}

#[test]
fn compact_switch_words_keep_link_order_and_reduce_small_comparisons() {
    for (cases,words) in [(vec![],0),(vec![(0,7)],4),(vec![(1,7)],5),
        (vec![(0,7),(4095,11),(0,15)],11),(vec![(4096,7)],7)] {
        let mut a=Assembler::default();a.switch_cases(&cases).unwrap();
        assert_eq!(a.words.len(),words);
        assert_eq!(a.links.iter().map(|(_,target)|*target).collect::<Vec<_>>(),
            cases.iter().map(|(_,target)|*target).collect::<Vec<_>>());
        assert!(a.links.iter().all(|(at,_)|a.words[*at]==0x14000000));
    }
}

#[test]
fn compact_switch_zero_preserves_both_halves_at_every_budget() {
    let p=dispatch(&[0]);
    for value in [0,1,1<<63,1<<64,1<<127,u128::MAX] {
        compare(&p,&[value],if value==0 {1} else {999});
    }
}

#[test]
fn compact_switch_small_cases_preserve_first_match_and_wide_default() {
    let cases=[0,4095,1,0];let p=dispatch(&cases);
    for value in [0,1,4095,4096,1<<64,(1<<64)|4095,u128::MAX] {
        let expected=cases.iter().position(|v|*v==value).map_or(999,|i|i as u128+1);
        compare(&p,&[value],expected);
    }
}

#[test]
fn compact_switch_general_cases_keep_full_width_and_duplicate_order() {
    let cases=[1<<64,4096,u128::MAX,1<<64];let p=dispatch(&cases);
    for value in [0,4095,4096,1<<64,1<<127,u128::MAX] {
        let expected=cases.iter().position(|v|*v==value).map_or(999,|i|i as u128+1);
        compare(&p,&[value],expected);
    }
}

#[test]
fn compact_switch_backward_edges_keep_exact_logical_counts() {
    let p=program(vec![Op::Local{dst:0,offset:16},Op::Load{dst:1,address:0,size:16},
        Op::Imm{dst:2,value:1},Op::Switch{value:1,cases:vec![(0,6)],otherwise:4},
        Op::Binary{dst:1,overflow:3,op:Binary::Sub,a:1,b:2,bits:128,signed:false},
        Op::Jump{target:3},Op::Local{dst:0,offset:0},Op::Store{address:0,src:1,size:16},Op::Return],8,1);
    for value in [0,1,3] {compare(&p,&[value],0);}
}

#[cfg(all(target_arch="aarch64",target_os="macos"))]
std::arch::global_asm!(r#"
    .text
    .p2align 2
    .globl _rust_interp_compact_switch_encoding
_rust_interp_compact_switch_encoding:
    orr x11,x9,x10
    cmp x11,xzr
    cmp x10,xzr
    cmp x9,#0
    cmp x9,#1
    cmp x9,#4095
"#);

#[test]
#[cfg(all(target_arch="aarch64",target_os="macos"))]
fn compact_switch_new_words_match_platform_assembler() {
    unsafe extern "C" {static rust_interp_compact_switch_encoding:[u32;6];}
    let mut a=Assembler::default();a.three(0xaa000000,11,9,10);a.cmp(11,31);a.cmp(10,31);
    for value in [0,1,4095] {a.emit(0xf100001f | (value<<10) | (9<<5));}
    assert_eq!(a.words,unsafe {rust_interp_compact_switch_encoding});
}

#[test]
fn compact_switch_empty_tables_keep_default_for_wide_values() {
    let p=dispatch(&[]);
    for value in [0,1,1<<64,1<<127,u128::MAX] {compare(&p,&[value],999);}
}
