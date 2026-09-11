use rust_interp_bytecode::{
    DEFAULT_ALLOCATION_LIMIT, MAX_ALLOCATION_LIMIT, Engine, Function, Limits, Op, Program, Slot,
    VERSION, execute_with_engine,
};

fn engines() -> Vec<Engine> {
    if cfg!(all(target_os="macos",target_arch="aarch64")) {
        vec![Engine::Interpreter,Engine::Jit]
    } else { vec![Engine::Interpreter] }
}

fn program(code: Vec<Op>) -> Program {
    Program { version:VERSION,target:"aarch64-apple-darwin".into(),entry:0,
        data:vec![],statics:vec![0x39;16],thread_locals:vec![],
        functions:vec![Function {name:"entry".into(),registers:8,frame_size:16,frame_align:16,
            args:vec![],result:Slot {offset:0,size:8},code}] }
}

fn allocation_program() -> Program {
    program(vec![
        Op::Imm {dst:0,value:8}, Op::Imm {dst:1,value:8},
        Op::Allocate {dst:2,size:0,align:1,zeroed:false},
        Op::Allocate {dst:3,size:0,align:1,zeroed:true},
        Op::Local {dst:4,offset:0},Op::Store {address:4,src:3,size:8},Op::Return,
    ])
}

#[test]
fn count_limit_is_exact_and_resets_for_each_execution() {
    let p=allocation_program();
    for engine in engines() {
        for limit in [0,1,2,MAX_ALLOCATION_LIMIT,1,2] {
            let r=execute_with_engine(&p,&[],Limits {allocations:limit,..Limits::default()},engine).unwrap();
            assert_eq!(r.value==0,limit<2);
            assert_eq!(r.instructions,7);
        }
    }
    assert_eq!(Limits::default().allocations,100_000);
    assert_eq!(DEFAULT_ALLOCATION_LIMIT,100_000);
}

#[test]
fn count_budget_does_not_override_byte_budget_and_statics_need_no_count_slot() {
    let p=allocation_program();
    for engine in engines() {
        // 128 register bytes + 16 null-address prefix + 16 frame + 16 statics.
        assert_eq!(execute_with_engine(&p,&[],Limits {memory:175,allocations:MAX_ALLOCATION_LIMIT,..Limits::default()},engine).unwrap_err(),
            "interpreter working-memory limit exceeded");
        for memory in [176,184,192] {
            let r=execute_with_engine(&p,&[],Limits {memory,allocations:MAX_ALLOCATION_LIMIT,..Limits::default()},engine).unwrap();
            assert_eq!(r.value==0,memory<192);
        }
        let p=program(vec![Op::Local {dst:0,offset:0},Op::Imm {dst:1,value:17},
            Op::Store {address:0,src:1,size:8},Op::Return]);
        assert_eq!(execute_with_engine(&p,&[],Limits {allocations:0,..Limits::default()},engine).unwrap().value,17);
    }
}

#[test]
fn excessive_count_limit_is_rejected_for_both_engines() {
    let p=allocation_program();
    for engine in engines() {
        for limit in [MAX_ALLOCATION_LIMIT+1,usize::MAX] {
            assert_eq!(execute_with_engine(&p,&[],Limits {allocations:limit,..Limits::default()},engine).unwrap_err(),
                "live allocation limit exceeds supported maximum of 1000000");
        }
    }
}

#[test]
fn cli_rejects_invalid_count_limits_before_reading_an_artifact() {
    for args in [vec!["--allocation-limit","1000001","absent.rbc"],
                 vec!["--allocation-limit","18446744073709551615","absent.rbc"],
                 vec!["--allocation-limit","-1","absent.rbc"],
                 vec!["--allocation-limit"]] {
        let result=std::process::Command::new(env!("CARGO_BIN_EXE_rust-interp-vm")).args(args).output().unwrap();
        assert!(!result.status.success());
        let message=String::from_utf8(result.stderr).unwrap();
        assert!(!message.contains("No such file"),"{message}");
    }
}
