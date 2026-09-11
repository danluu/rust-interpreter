use super::*;
use crate::{Engine, Limits, Slot, VERSION, execute_profiled, execute_with_engine};

const WIDE: u128 = 0xfedc_ba98_7654_3210_0123_4567_89ab_cdef;

fn program(code: Vec<Op>, registers: usize, args: usize) -> Program {
    Program { version: VERSION, target: "aarch64-apple-darwin".into(), entry: 0,
        data: vec![0; 64], statics: vec![], thread_locals: vec![],
        functions: vec![Function { name: "register_cache".into(), frame_size: 256, frame_align: 16,
            registers, args: (0..args).map(|n| Slot { offset: 16+n*16, size: 16 }).collect(),
            result: Slot { offset: 0, size: 16 }, code }] }
}

fn check(p: &Program, args: &[u128], expected: u128, max_budget: u64) {
    crate::validate(p).unwrap();
    let complete = execute_with_engine(p, args, Limits { instructions: max_budget, ..Limits::default() }, Engine::Interpreter).unwrap();
    assert_eq!(complete.value, expected);
    let budgets: Vec<_> = if max_budget < 160 { (0..=max_budget).collect() }
        else { vec![0,1,2,3,1023,1024,1025,1026,max_budget-2,max_budget-1,max_budget] };
    for budget in budgets {
        for capacity in [0, MAX_CODE_BYTES] {
            let limits = || Limits { instructions: budget, jit_code_bytes: capacity, ..Limits::default() };
            let reference = execute_profiled(p,args,limits(),Engine::Interpreter);
            let normal = execute_with_engine(p,args,limits(),Engine::Jit);
            let observed = execute_profiled(p,args,limits(),Engine::Jit);
            match reference {
                Err(error) => {
                    assert_eq!(normal.unwrap_err(),error,"budget={budget}");
                    assert_eq!(observed.unwrap_err(),error,"budget={budget}");
                }
                Ok((reference, reference_profile)) => {
                    let normal = normal.unwrap();
                    let (observed, profile) = observed.unwrap();
                    assert_eq!(normal.value,reference.value);
                    assert_eq!(observed.value,reference.value);
                    assert_eq!(normal.instructions,reference.instructions);
                    assert_eq!(observed.instructions,reference.instructions);
                    assert_eq!(normal.jit_entries,observed.jit_entries);
                    assert_eq!(normal.jit_instructions,observed.jit_instructions);
                    for (f,r) in profile.functions.iter().zip(&reference_profile.functions) {
                        let mut logical = f.interpreted.clone();
                        for (start,&hits) in f.jit_blocks.iter().enumerate() {
                            if hits != 0 { for count in &mut logical[start..f.jit_block_ends[start]] { *count += hits; } }
                        }
                        assert_eq!(logical,r.interpreted);
                    }
                }
            }
        }
    }
}

#[test]
fn cached_dynamic_values_survive_pressure_aliases_and_far_registers() {
    for r in [0,2050] {
        for (a,b) in [(WIDE,!WIDE),(0,u128::MAX),(1<<127,1<<64)] {
            let p = program(vec![
                Op::Local {dst:r,offset:16}, Op::Load {dst:r+1,address:r,size:16},
                Op::Local {dst:r,offset:32}, Op::Load {dst:r+2,address:r,size:16},
                Op::Binary {dst:r+1,overflow:r+3,op:Binary::Sub,a:r+1,b:r+2,bits:128,signed:false},
                Op::Local {dst:r,offset:0}, Op::Store {address:r,src:r+1,size:16}, Op::Return,
            ],r as usize+4,2);
            check(&p,&[a,b],a.wrapping_sub(b),10);
        }
    }
}

#[test]
fn cached_dynamic_values_survive_medium_copy_scratch_clobbers() {
    for size in 17..=32 {
        // Load the source pointer through memory so it owns the dynamic cache.
        // Its final read occurs in Copy itself, before x5/x6 become scratch.
        let p = program(vec![
            Op::Local {dst:0,offset:16}, Op::Local {dst:1,offset:96},
            Op::Store {address:1,src:0,size:8}, Op::Load {dst:2,address:1,size:8},
            Op::Local {dst:3,offset:128}, Op::Copy {dst:3,src:2,size},
            Op::Load {dst:4,address:3,size:16}, Op::Local {dst:5,offset:0},
            Op::Store {address:5,src:4,size:16}, Op::Return,
        ],6,2);
        check(&p,&[WIDE,!WIDE],WIDE,12);
    }
    // A cached value unrelated to either pointer is still live after Copy.
    let p = program(vec![
        Op::Local {dst:0,offset:16}, Op::Load {dst:1,address:0,size:16},
        Op::Local {dst:2,offset:128}, Op::Copy {dst:2,src:0,size:24},
        Op::Local {dst:0,offset:0}, Op::Store {address:0,src:1,size:16}, Op::Return,
    ],3,2);
    check(&p,&[WIDE,!WIDE],WIDE,10);
}

#[test]
fn cached_dynamic_values_survive_read_before_write_backedges() {
    let p=program(vec![
        Op::Local {dst:0,offset:16}, Op::Load {dst:1,address:0,size:8},
        Op::Imm {dst:2,value:1}, Op::Jump {target:4},
        Op::Binary {dst:1,overflow:3,op:Binary::Sub,a:1,b:2,bits:64,signed:false},
        Op::Local {dst:0,offset:0}, Op::Store {address:0,src:1,size:16},
        Op::Switch {value:1,cases:vec![(0,8)],otherwise:4}, Op::Return,
    ],4,1);
    for n in [1,2,9] { check(&p,&[n],0,45); }
}

#[test]
fn cached_dynamic_values_survive_interpreter_fallback_and_high_halves() {
    let p=program(vec![
        Op::Local {dst:0,offset:16}, Op::Load {dst:1,address:0,size:16},
        Op::Local {dst:2,offset:32}, Op::Load {dst:3,address:2,size:16},
        Op::Binary {dst:1,overflow:4,op:Binary::Sub,a:1,b:3,bits:128,signed:false},
        Op::Unary {dst:1,src:1,op:Unary::CountOnes,bits:128},
        Op::Local {dst:0,offset:0}, Op::Store {address:0,src:1,size:16}, Op::Return,
    ],5,2);
    for (a,b) in [(WIDE,1), (1<<127,1<<64), (0,1)] {
        check(&p,&[a,b],a.wrapping_sub(b).count_ones() as u128,12);
    }
}

#[test]
fn cached_dynamic_overwrites_and_zero_upper_halves_are_ordered() {
    for (dst,overflow) in [(1,4),(4,1),(1,1),(3,3)] {
        let p=program(vec![
            Op::Local {dst:0,offset:16}, Op::Load {dst:1,address:0,size:16},
            Op::Local {dst:2,offset:32}, Op::Load {dst:3,address:2,size:8},
            Op::Binary {dst,overflow,op:Binary::Sub,a:1,b:3,bits:128,signed:false},
            Op::Local {dst:0,offset:0}, Op::Store {address:0,src:dst,size:16}, Op::Return,
        ],5,2);
        for a in [0,WIDE,u128::MAX] {
            let (value,flag)=a.overflowing_sub(1);
            check(&p,&[a,1],if dst==overflow {flag as u128} else {value},11);
        }
    }
    let p=program(vec![
        Op::Local {dst:0,offset:16}, Op::Load {dst:1,address:0,size:16},
        Op::Imm {dst:1,value:7}, Op::Local {dst:0,offset:0},
        Op::Store {address:0,src:1,size:16}, Op::Return,
    ],2,1);
    check(&p,&[WIDE],7,9);
}

#[test]
fn cached_dynamic_branch_values_keep_full_width_and_native_successors() {
    for value in [0,1,1<<64,WIDE] {
        let p=program(vec![
            Op::Local {dst:0,offset:16}, Op::Load {dst:1,address:0,size:16},
            Op::Switch {value:1,cases:vec![(0,3),(1,7),(1<<64,11)],otherwise:15},
            Op::Imm {dst:2,value:5}, Op::Local {dst:0,offset:0}, Op::Store {address:0,src:2,size:16}, Op::Return,
            Op::Imm {dst:2,value:6}, Op::Local {dst:0,offset:0}, Op::Store {address:0,src:2,size:16}, Op::Return,
            Op::Imm {dst:2,value:7}, Op::Local {dst:0,offset:0}, Op::Store {address:0,src:2,size:16}, Op::Return,
            Op::Local {dst:0,offset:0}, Op::Store {address:0,src:1,size:16}, Op::Jump {target:18}, Op::Return,
        ],3,1);
        check(&p,&[value],match value {0=>5,1=>6,n if n==1<<64=>7,n=>n},12);
    }
}

#[test]
fn cached_dynamic_values_survive_forced_region_split() {
    let mut code=vec![Op::Local {dst:0,offset:16},Op::Load {dst:1,address:0,size:8},Op::Imm {dst:2,value:1}];
    for _ in 0..1030 { code.push(Op::Binary {dst:1,overflow:3,op:Binary::Add,a:1,b:2,bits:64,signed:false}); }
    code.extend([Op::Local {dst:0,offset:0},Op::Store {address:0,src:1,size:16},Op::Return]);
    check(&program(code,4,1),&[123],1153,1038);
}

#[test]
fn cached_dynamic_assertion_and_division_faults_keep_budget_order() {
    for assertion in [false,true] {
        let mut code=vec![Op::Local {dst:0,offset:16},Op::Load {dst:1,address:0,size:16},Op::Imm {dst:2,value:0}];
        code.push(if assertion { Op::Assert {value:1,expected:false,message:"cache fault".into()} }
            else { Op::Binary {dst:3,overflow:4,op:Binary::Div,a:1,b:2,bits:64,signed:false} });
        code.extend([Op::Trap {message:"later fault".into()},Op::Return]);
        let p=program(code,5,1);
        for budget in 0..=8 {
            let limits=|| Limits {instructions:budget,..Limits::default()};
            let expected=execute_with_engine(&p,&[WIDE],limits(),Engine::Interpreter).unwrap_err();
            assert_eq!(execute_with_engine(&p,&[WIDE],limits(),Engine::Jit).unwrap_err(),expected);
            assert_eq!(execute_profiled(&p,&[WIDE],limits(),Engine::Jit).unwrap_err(),expected);
        }
    }
}


#[test]
fn packed_narrow_values_keep_pressure_aliases_and_zero_high_halves() {
    for r in [0, 2050] {
        for size in [1, 2, 4, 8] {
            for (dst, flag) in [(1,4), (2,1), (3,2), (1,1)] {
                for (a,b,c) in [(WIDE,!WIDE,9), (u128::MAX,1,0), (0,0,WIDE)] {
                    let mask = (1u128 << (size*8)) - 1;
                    let sum = ((a & mask)+(b & mask)) & mask;
                    let overflow = (a & mask)+(b & mask) > mask;
                    let value = if dst==flag { overflow as u128 } else { sum };
                    // The third loaded value creates pressure. It is live
                    // after the aliased arithmetic unless explicitly replaced.
                    let tail = if dst==3 {value} else if flag==3 {overflow as u128} else {c & mask};
                    let p=program(vec![
                        Op::Local {dst:r,offset:16}, Op::Load {dst:r+1,address:r,size},
                        Op::Local {dst:r,offset:32}, Op::Load {dst:r+2,address:r,size},
                        Op::Local {dst:r,offset:48}, Op::Load {dst:r+3,address:r,size},
                        Op::Binary {dst:r+dst,overflow:r+flag,op:Binary::Add,a:r+1,b:r+2,bits:(size*8) as u8,signed:false},
                        Op::Binary {dst:r+5,overflow:r+6,op:Binary::Sub,a:r+dst,b:r+3,bits:128,signed:false},
                        Op::Local {dst:r,offset:0}, Op::Store {address:r,src:r+5,size:16}, Op::Return,
                    ],r as usize+7,3);
                    check(&p,&[a,b,c],value.wrapping_sub(tail),14);
                }
            }
        }
    }
}

#[test]
fn packed_pair_survives_medium_copy_with_two_live_values_or_pointers() {
    for size in 17..=32 {
        let p=program(vec![
            Op::Local {dst:0,offset:16}, Op::Load {dst:1,address:0,size:8},
            Op::Local {dst:0,offset:32}, Op::Load {dst:2,address:0,size:8},
            Op::Local {dst:3,offset:128}, Op::Local {dst:4,offset:16},
            Op::Copy {dst:3,src:4,size},
            Op::Binary {dst:5,overflow:6,op:Binary::Sub,a:1,b:2,bits:128,signed:false},
            Op::Local {dst:0,offset:0}, Op::Store {address:0,src:5,size:16}, Op::Return,
        ],7,2);
        check(&p,&[WIDE,!WIDE],(WIDE as u64 as u128).wrapping_sub(!WIDE as u64 as u128),14);
        let p=program(vec![
            Op::Local {dst:0,offset:16}, Op::Local {dst:1,offset:96}, Op::Store {address:1,src:0,size:8},
            Op::Local {dst:0,offset:128}, Op::Local {dst:2,offset:104}, Op::Store {address:2,src:0,size:8},
            Op::Load {dst:3,address:1,size:8}, Op::Load {dst:4,address:2,size:8},
            Op::Copy {dst:4,src:3,size}, Op::Load {dst:5,address:4,size:16},
            Op::Local {dst:0,offset:0}, Op::Store {address:0,src:5,size:16}, Op::Return,
        ],6,2);
        check(&p,&[WIDE,!WIDE],WIDE,16);
    }
}

#[test]
fn packed_cache_transitions_between_narrow_pair_and_wide_value() {
    for (a,b,c) in [(WIDE,!WIDE,1<<127), (0,u128::MAX,u128::MAX), (1<<64,17,WIDE)] {
        for dst in [1,2,3,4] {
            let p=program(vec![
                Op::Local {dst:0,offset:16}, Op::Load {dst:1,address:0,size:8},
                Op::Local {dst:0,offset:32}, Op::Load {dst:2,address:0,size:8},
                Op::Local {dst:0,offset:48}, Op::Load {dst:3,address:0,size:16},
                Op::Binary {dst,overflow:5,op:Binary::Sub,a:3,b:1,bits:128,signed:false},
                Op::Binary {dst:6,overflow:7,op:Binary::Sub,a:dst,b:2,bits:128,signed:false},
                Op::Local {dst:0,offset:0}, Op::Store {address:0,src:6,size:16}, Op::Return,
            ],8,3);
            let first=c.wrapping_sub(a as u64 as u128);
            check(&p,&[a,b,c],first.wrapping_sub(if dst==2 {first} else {b as u64 as u128}),14);
        }
    }
}

#[test]
fn packed_pair_preserves_two_read_before_write_values_on_backedges() {
    let p=program(vec![
        Op::Local {dst:0,offset:16}, Op::Load {dst:1,address:0,size:8},
        Op::Local {dst:0,offset:32}, Op::Load {dst:2,address:0,size:8},
        Op::Imm {dst:3,value:1}, Op::Jump {target:6},
        Op::Binary {dst:2,overflow:4,op:Binary::Add,a:1,b:2,bits:64,signed:false},
        Op::Binary {dst:1,overflow:4,op:Binary::Sub,a:1,b:3,bits:64,signed:false},
        Op::Switch {value:1,cases:vec![(0,9)],otherwise:6},
        Op::Local {dst:0,offset:0}, Op::Store {address:0,src:2,size:16}, Op::Return,
    ],5,2);
    for n in [1,2,9] { check(&p,&[n,37],37+n*(n+1)/2,40); }
}
