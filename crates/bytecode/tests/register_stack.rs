use rust_interp_bytecode::{
    Binary, Engine, Function, Limits, Op, Program, Slot, VERSION, execute_with_engine,
};

#[test]
fn growing_and_reusing_register_storage_preserves_callers_and_zeroes_new_activations() {
    let magic = 0xfedcba98765432100123456789abcdefu128;
    let make_callee = |name: &str, code| Function {
        name: name.into(), frame_size: 16, frame_align: 16, registers: 8193,
        args: vec![], result: Slot {offset: 0,size: 16}, code,
    };
    let p = Program {
        version: VERSION, target: "aarch64-apple-darwin".into(), entry: 0,
        data: vec![0;16], statics: vec![], thread_locals: vec![],
        functions: vec![
            Function {
                name: "caller".into(), frame_size: 32,frame_align: 16,registers: 5,
                args: vec![],result: Slot {offset: 0,size: 16},
                code: vec![
                    Op::Local {dst: 0,offset: 0},
                    Op::Imm {dst: 1,value: magic},
                    Op::Local {dst: 2,offset: 16},
                    Op::Call {function: 1,args: vec![],destination: 2},
                    Op::Call {function: 2,args: vec![],destination: 2},
                    Op::Load {dst: 3,address: 2,size: 16},
                    Op::Binary {dst: 3,overflow: 4,op: Binary::Eq,a: 3,b: 4,bits: 128,signed: false},
                    Op::Assert {value: 3,expected: true,message: "new activation was not zeroed".into()},
                    Op::Store {address: 0,src: 1,size: 16},
                    Op::Return,
                ],
            },
            make_callee("smear",vec![
                Op::Local {dst: 0,offset: 0},
                Op::Imm {dst: 8192,value: magic},
                Op::Store {address: 0,src: 8192,size: 16},
                Op::Return,
            ]),
            make_callee("read-zero",vec![
                Op::Local {dst: 0,offset: 0},
                Op::Imm {dst: 1,value: 0},
                Op::Store {address: 0,src: 8192,size: 16},
                Op::Return,
            ]),
        ],
    };
    let mut engines = vec![Engine::Interpreter];
    if cfg!(all(target_arch="aarch64",target_os="macos")) {engines.push(Engine::Jit);}
    // Exact live bytes: data 16 + caller frame 32 + callee frame 16,
    // plus the simultaneously live caller and callee u128 registers.
    let memory = 64 + (5 + 8193) * 16;
    for engine in engines {
      for read_zero in [
        p.functions[2].code.clone(),
        vec![
            Op::Local {dst: 0,offset: 0},
            Op::Jump {target: 3},
            Op::Imm {dst: 8192,value: magic},
            Op::Store {address: 0,src: 8192,size: 16},
            Op::Return,
        ],
        vec![
            Op::Local {dst: 0,offset: 0},
            Op::Switch {value: 8192,cases: vec![(0,3)],otherwise: 2},
            Op::Trap {message: "stale register reached a branch".into()},
            Op::Store {address: 0,src: 8192,size: 16},
            Op::Return,
        ],
      ] {
        let mut p=p.clone();
        p.functions[2].code=read_zero;
        let result = execute_with_engine(&p,&[],Limits {memory,frames: 2,..Limits::default()},engine).unwrap();
        assert_eq!(result.value,magic);
        assert_eq!(result.instructions,18);
        let error = execute_with_engine(&p,&[],Limits {memory: memory-1,..Limits::default()},engine).unwrap_err();
        assert!(error.contains("working-memory limit"),"{error}");
        let error = execute_with_engine(&p,&[],Limits {frames: 1,..Limits::default()},engine).unwrap_err();
        assert!(error.contains("call-depth"),"{error}");
      }
    }
}
