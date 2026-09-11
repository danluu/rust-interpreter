use rust_interp_bytecode::{
    Binary, Engine, Function, Limits, Op, Program, Slot, VERSION,
    execute_with_engine, remove_fallthrough_jumps,
};

fn program(code: Vec<Op>) -> Program {
    Program {
        version: VERSION,target: "aarch64-apple-darwin".into(),entry: 0,
        data: vec![0;16],statics: vec![], thread_locals: vec![],
        functions: vec![Function {
            name: "control-flow".into(),frame_size: 16,frame_align: 8,registers: 4,
            args: vec![Slot {offset: 0,size: 8}],result: Slot {offset: 8,size: 8},code,
        }],
    }
}

fn equivalent(original: &Program, inputs: &[(u128,u128)], removed: usize) {
    let mut optimized=original.clone();
    assert_eq!(remove_fallthrough_jumps(&mut optimized.functions[0].code).unwrap(),removed);
    // The pass must be idempotent even when a branch targets a removed chain.
    assert_eq!(remove_fallthrough_jumps(&mut optimized.functions[0].code).unwrap(),0);
    let mut engines=vec![Engine::Interpreter];
    if cfg!(all(target_arch="aarch64",target_os="macos")) {engines.push(Engine::Jit);}
    for engine in engines {
        for &(input,want) in inputs {
            let before=execute_with_engine(original,&[input],Limits::default(),engine).unwrap();
            let after=execute_with_engine(&optimized,&[input],Limits::default(),engine).unwrap();
            assert_eq!(before.value,want);
            assert_eq!(after.value,want);
            assert!(after.instructions < before.instructions);
        }
    }
}

#[test]
fn entry_and_branch_targets_follow_removed_jump_chains() {
    let p=program(vec![
        Op::Jump {target: 1},Op::Jump {target: 2},
        Op::Imm {dst: 0,value: 41},
        Op::Jump {target: 4},
        Op::Local {dst: 1,offset: 8},
        Op::Store {address: 1,src: 0,size: 8},
        Op::Return,
    ]);
    equivalent(&p,&[(0,41)],3);
    let mut p=p;
    // The first jump becomes redundant only after the second is removed.
    p.functions[0].code[0]=Op::Jump {target: 2};
    equivalent(&p,&[(0,41)],3);
    let p=program(vec![
        Op::Local {dst: 0,offset: 0},
        Op::Load {dst: 1,address: 0,size: 8},
        Op::Switch {value: 1,cases: vec![(0,3),(1,6)],otherwise: 9},
        Op::Jump {target: 4},
        Op::Imm {dst: 2,value: 11},
        Op::Jump {target: 12},
        Op::Jump {target: 7},
        Op::Imm {dst: 2,value: 22},
        Op::Jump {target: 12},
        Op::Jump {target: 10},
        Op::Imm {dst: 2,value: 33},
        Op::Jump {target: 12},
        Op::Local {dst: 0,offset: 8},
        Op::Store {address: 0,src: 2,size: 8},
        Op::Return,
    ]);
    equivalent(&p,&[(0,11),(1,22),(2,33),(u64::MAX as u128,33)],4);
}

#[test]
fn loop_backedges_survive_remapping() {
    let p=program(vec![
        Op::Jump {target: 1},
        Op::Local {dst: 0,offset: 0},
        Op::Load {dst: 1,address: 0,size: 8},
        Op::Imm {dst: 2,value: 1},
        Op::Binary {dst: 1,overflow: 3,op: Binary::Sub,a: 1,b: 2,bits: 64,signed: false},
        Op::Jump {target: 6},
        Op::Switch {value: 1,cases: vec![(0,9)],otherwise: 7},
        Op::Jump {target: 8},
        Op::Jump {target: 3},
        Op::Jump {target: 10},
        Op::Local {dst: 0,offset: 8},
        Op::Store {address: 0,src: 1,size: 8},
        Op::Return,
    ]);
    equivalent(&p,&[(1,0),(2,0),(7,0)],4);
}

#[test]
fn invalid_targets_are_rejected_without_mutating_the_body() {
    for mut code in [
        vec![],
        vec![Op::Jump {target: 1}],
        vec![Op::Jump {target: 1},Op::Switch {value: 0,cases: vec![(0,2)],otherwise: 0}],
        vec![Op::Jump {target: 1},Op::Switch {value: 0,cases: vec![],otherwise: 2}],
    ] {
        let before=bincode::serialize(&code).unwrap();
        assert!(remove_fallthrough_jumps(&mut code).is_err());
        assert_eq!(bincode::serialize(&code).unwrap(),before);
    }
}
