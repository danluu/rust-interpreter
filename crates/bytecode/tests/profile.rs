use rust_interp_bytecode::{
    Binary, Engine, Function, Limits, Op, Program, Slot, VERSION,
    execute_profiled, execute_with_engine,
};

#[test]
fn profile_counts_calls_branches_and_compiled_blocks_without_changing_execution() {
    let p = Program {
        version: VERSION, target: "aarch64-apple-darwin".into(), entry: 0,
        data: vec![0;16], statics: vec![], thread_locals: vec![],
        functions: vec![
            Function {
                name: "loop".into(), frame_size: 8, frame_align: 8, registers: 3,
                args: vec![], result: Slot {offset: 0, size: 8},
                code: vec![
                    Op::Local {dst: 0, offset: 0},
                    Op::Imm {dst: 1, value: 4},
                    Op::Store {address: 0, src: 1, size: 8},
                    Op::Call {function: 1, args: vec![0], destination: 0},
                    Op::Load {dst: 2, address: 0, size: 8},
                    Op::Switch {value: 2, cases: vec![(0,7)], otherwise: 3},
                    Op::Trap {message: "unreachable".into()},
                    Op::Return,
                ],
            },
            Function {
                name: "decrement".into(), frame_size: 8, frame_align: 8, registers: 4,
                args: vec![Slot {offset: 0,size: 8}], result: Slot {offset: 0,size: 8},
                code: vec![
                    Op::Local {dst: 0,offset: 0},
                    Op::Load {dst: 1,address: 0,size: 8},
                    Op::Imm {dst: 2,value: 1},
                    Op::Binary {dst: 1,overflow: 3,op: Binary::Sub,a: 1,b: 2,bits: 64,signed: false},
                    Op::Store {address: 0,src: 1,size: 8},
                    Op::Return,
                ],
            },
        ],
    };
    let mut engines = vec![Engine::Interpreter];
    if cfg!(all(target_arch="aarch64",target_os="macos")) { engines.push(Engine::Jit); }
    for engine in engines {
        let limits = || Limits {instructions: 40,..Limits::default()};
        let ordinary = execute_with_engine(&p,&[],limits(),engine).unwrap();
        let (observed,profile) = execute_profiled(&p,&[],limits(),engine).unwrap();
        assert_eq!(ordinary.value,0);
        assert_eq!(observed.value,ordinary.value);
        assert_eq!(observed.instructions,40);
        assert_eq!(observed.instructions,ordinary.instructions);
        assert_eq!(observed.jit_instructions,ordinary.jit_instructions);
        let mut compiled = 0;
        for (row,want) in profile.functions.iter().zip([vec![1,1,1,4,4,4,0,1],vec![4;6]]) {
            let mut counts = row.interpreted.clone();
            for (pc,(&hits,&end)) in row.jit_blocks.iter().zip(&row.jit_block_ends).enumerate() {
                if hits != 0 {
                    assert!(end > pc);
                    for count in &mut counts[pc..end] { *count += hits; compiled += hits; }
                }
            }
            assert_eq!(counts,want);
        }
        assert_eq!(compiled,observed.jit_instructions);
        for limit in [1,4,5,9,39] {
            let limits = || Limits {instructions: limit,..Limits::default()};
            let ordinary = execute_with_engine(&p,&[],limits(),engine).unwrap_err();
            let observed = execute_profiled(&p,&[],limits(),engine).unwrap_err();
            assert_eq!(observed,ordinary);
        }
    }
}
