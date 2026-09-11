use super::*;
use rust_interp_bytecode::{Binary,Engine,Function,Limits,Program,Slot,VERSION,execute_with_engine};
fn mov(dst:Reg,src:Reg)->Op {Op::Cast{dst,src,from:64,to:64,signed:false}}
fn check(code:Vec<Op>,expected:u128,removed:usize) {
    let f=Function{name:"move-captures".into(),frame_size:16,frame_align:16,registers:8,args:vec![],result:Slot{offset:0,size:8},code};
    let p=Program{version:VERSION,target:"aarch64-apple-darwin".into(),entry:0,functions:vec![f],data:vec![],statics:vec![],thread_locals:vec![]};
    let mut q=p.clone();assert_eq!(eliminate(&mut q.functions[0].code,8,&[(0,64)]),removed);
    let mut engines=vec![Engine::Interpreter];if cfg!(all(target_arch="aarch64",target_os="macos")){engines.push(Engine::Jit);}
    for program in [&p,&q] {for &engine in &engines {for capacity in [0,16*1024*1024] {
        let result=execute_with_engine(program,&[],Limits{jit_code_bytes:capacity,..Limits::default()},engine).unwrap();assert_eq!(result.value,expected);
        assert_eq!(execute_with_engine(program,&[],Limits{instructions:result.instructions-1,jit_code_bytes:capacity,..Limits::default()},engine).unwrap_err(),"interpreter instruction limit exceeded");
    }}}
}
#[test]
fn scalar_moves_forward_only_live_canonical_versions() {
    check(vec![Op::Imm{dst:0,value:7},mov(1,0),Op::Imm{dst:2,value:3},
        Op::Binary{dst:3,overflow:4,op:Binary::Add,a:1,b:2,bits:64,signed:false},
        Op::Local{dst:5,offset:0},Op::Store{address:5,src:3,size:8},Op::Return],10,1);
    check(vec![Op::Imm{dst:0,value:7},mov(1,0),Op::Imm{dst:0,value:19},
        Op::Local{dst:5,offset:0},Op::Store{address:5,src:1,size:8},Op::Return],7,0);
    // Read before the same opcode overwrites the canonical source.
    check(vec![Op::Imm{dst:0,value:7},mov(1,0),Op::Imm{dst:2,value:3},
        Op::Binary{dst:0,overflow:4,op:Binary::Add,a:1,b:2,bits:64,signed:false},
        Op::Local{dst:5,offset:0},Op::Store{address:5,src:0,size:8},Op::Return],10,1);
}
#[test]
fn scalar_moves_keep_captures_read_after_block_boundaries() {
    check(vec![Op::Imm{dst:0,value:7},mov(1,0),Op::Jump{target:3},
        Op::Imm{dst:0,value:19},Op::Local{dst:5,offset:0},Op::Store{address:5,src:1,size:8},Op::Return],7,0);
    check(vec![Op::Imm{dst:0,value:7},Op::Imm{dst:2,value:0},mov(1,0),
        Op::Switch{value:2,cases:vec![(0,6)],otherwise:4},Op::Imm{dst:0,value:19},Op::Jump{target:6},
        Op::Local{dst:5,offset:0},Op::Store{address:5,src:1,size:8},Op::Return],7,0);
}
#[test]
fn scalar_moves_preserve_narrow_casts_and_overwritten_temporary_registers() {
    check(vec![Op::Imm{dst:0,value:0x1234},Op::Cast{dst:1,src:0,from:64,to:8,signed:false},
        Op::Local{dst:5,offset:0},Op::Store{address:5,src:1,size:8},Op::Return],0x34,0);
    check(vec![Op::Imm{dst:0,value:7},mov(1,0),Op::Imm{dst:1,value:23},
        Op::Local{dst:5,offset:0},Op::Store{address:5,src:1,size:8},Op::Return],23,0);
}
