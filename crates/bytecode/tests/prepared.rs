#![cfg(all(target_arch = "aarch64", target_os = "macos"))]
use rust_interp_bytecode::{Binary, Engine, Execution, Function, Limits, Op, PreparedJit, Program,
    Slot, VERSION, FUNCTION_POINTER_TAG, HEAP_POINTER_TAG, execute_with_engine};

fn limits() -> Limits {
    Limits { jit_resumable_calls: true, jit_persistent_registers: true, ..Limits::default() }
}
fn function(name: &str, code: Vec<Op>) -> Function {
    Function { name: name.into(), frame_size: 32, frame_align: 16, registers: 8,
        args: vec![], result: Slot { offset: 0, size: 8 }, code }
}
fn program(functions: Vec<Function>) -> Program {
    Program { version: VERSION, target: "aarch64-apple-darwin".into(), entry: 0,
        functions, data: vec![0; 16], statics: vec![0; 48], thread_locals: vec![Slot { offset: 16, size: 8 }] }
}
fn value(name: &str, n: u128) -> Function {
    function(name, vec![Op::Local { dst: 0, offset: 0 }, Op::Imm { dst: 1, value: n },
        Op::Store { address: 0, src: 1, size: 8 }, Op::Return])
}
fn reference(p: &Program, entry: usize, args: &[u128], mut budget: Limits) -> Result<Execution, String> {
    let mut p = p.clone(); p.entry = entry;
    budget.jit_resumable_calls = false; budget.jit_persistent_registers = false;
    execute_with_engine(&p, args, budget, Engine::Interpreter)
}
fn same(actual: Result<Execution, String>, expected: Result<Execution, String>) -> Execution {
    let actual = actual.unwrap(); let expected = expected.unwrap();
    assert_eq!(actual.value, expected.value);
    assert_eq!(actual.instructions, expected.instructions);
    assert_eq!(actual.peak_memory, expected.peak_memory);
    actual
}

#[test]
fn distinct_entries_and_arguments_share_code_without_recompiling() {
    let mut shared = function("shared", vec![Op::Local { dst: 0, offset: 8 },
        Op::Load { dst: 1, address: 0, size: 8 }, Op::Imm { dst: 2, value: 3 },
        Op::Binary { dst: 1, overflow: 7, op: Binary::Mul, a: 1, b: 2, bits: 64, signed: false },
        Op::Local { dst: 0, offset: 0 }, Op::Store { address: 0, src: 1, size: 8 }, Op::Return]);
    shared.args = vec![Slot { offset: 8, size: 8 }];
    let mut first = function("first", vec![Op::Local { dst: 0, offset: 8 }, Op::Local { dst: 1, offset: 0 },
        Op::Call { function: 2, args: vec![0], destination: 1 }, Op::Return]);
    first.args = shared.args.clone();
    let mut second = first.clone(); second.name = "second".into();
    let p = program(vec![first, second, shared]);
    let mut prepared = PreparedJit::new(&p, &limits()).unwrap();
    assert!(prepared.preparation_nanos() > 0);
    for (index, (entry, argument)) in [(0, 7), (1, 11), (0, 3), (2, 19), (1, 17)].into_iter().enumerate() {
        let actual = same(prepared.execute_entry(entry, &[argument], limits()), reference(&p, entry, &[argument], limits()));
        assert_eq!(actual.value, argument * 3);
        assert!(actual.jit_instructions > 0);
        if index >= 2 { assert_eq!(actual.jit_compile_nanos, 0); }
    }
    assert_eq!(p.entry, 0);
}

#[test]
fn mutable_statics_and_tls_initializers_are_fresh_for_every_execution() {
    let mut code = vec![];
    for offset in [16, 32] {
        code.extend([Op::Imm { dst: 0, value: (HEAP_POINTER_TAG + offset) as u128 },
            Op::Load { dst: 1, address: 0, size: 8 },
            Op::Assert { value: 1, expected: false, message: "state leaked between executions".into() },
            Op::Imm { dst: 1, value: 99 }, Op::Store { address: 0, src: 1, size: 8 }]);
    }
    code.push(Op::Return);
    let p = program(vec![function("dirty globals", code)]);
    let mut prepared = PreparedJit::new(&p, &limits()).unwrap();
    for _ in 0..8 { same(prepared.execute(&[], limits()), reference(&p, 0, &[], limits())); }
    assert!(p.statics.iter().all(|&b| b == 0));
}

#[test]
fn failed_guest_and_leaked_allocations_do_not_poison_later_executions() {
    let allocate = function("allocation", vec![Op::Imm { dst: 0, value: 32 }, Op::Imm { dst: 1, value: 8 },
        Op::Allocate { dst: 2, size: 0, align: 1, zeroed: false }, Op::Return]);
    let mut fail = allocate.clone(); fail.name = "failure after allocation".into();
    fail.code[3] = Op::Trap { message: "intentional failure".into() };
    let p = program(vec![allocate, fail, value("clean", 42)]);
    let mut prepared = PreparedJit::new(&p, &limits()).unwrap();
    for _ in 0..8 {
        let one = || Limits { allocations: 1, ..limits() };
        same(prepared.execute_entry(0, &[], one()), reference(&p, 0, &[], one()));
        assert!(prepared.execute_entry(1, &[], one()).unwrap_err().contains("intentional failure"));
        assert_eq!(prepared.execute_entry(2, &[], Limits { allocations: 0, ..limits() }).unwrap().value, 42);
    }
}

#[test]
fn budgets_depth_and_memory_are_checked_again_after_code_is_prepared() {
    let p = program(vec![function("root", vec![Op::Local { dst: 0, offset: 0 },
        Op::Call { function: 1, args: vec![], destination: 0 }, Op::Return]), value("callee", 13)]);
    let mut prepared = PreparedJit::new(&p, &limits()).unwrap();
    let total = prepared.execute(&[], limits()).unwrap().instructions;
    for instructions in 0..=total {
        let run = || Limits { instructions, ..limits() };
        let actual = prepared.execute(&[], run()); let expected = reference(&p, 0, &[], run());
        if instructions < total { assert_eq!(actual.unwrap_err(), expected.unwrap_err()); }
        else { same(actual, expected); }
    }
    for budget in [Limits { frames: 1, ..limits() }, Limits { memory: 100, ..limits() },
                   Limits { allocations: usize::MAX, ..limits() }] {
        assert!(prepared.execute(&[], budget).is_err());
        assert_eq!(prepared.execute(&[], limits()).unwrap().value, 13);
    }
}

#[test]
fn option_entry_and_argument_errors_leave_the_prepared_owner_usable() {
    let mut f = value("argument", 5); f.args = vec![Slot { offset: 8, size: 1 }];
    let p = program(vec![f]);
    assert!(PreparedJit::new(&p, &Limits::default()).is_err());
    assert!(PreparedJit::new(&p, &Limits { jit_native_calls: true, ..limits() }).is_err());
    let mut invalid = p.clone(); invalid.functions[0].registers = 0;
    assert!(PreparedJit::new(&invalid, &limits()).is_err());
    let mut prepared = PreparedJit::new(&p, &limits()).unwrap();
    for bad in [Limits::default(), Limits { jit_code_bytes: 0, ..limits() },
                Limits { jit_persistent_registers: false, ..limits() },
                Limits { jit_native_call_stubs: true, ..limits() }] {
        assert!(prepared.execute(&[1], bad).is_err());
    }
    assert_eq!(prepared.execute_entry(99, &[], limits()).unwrap_err(), "missing entry function");
    assert_eq!(prepared.execute(&[], limits()).unwrap_err(), "wrong entry argument count");
    assert_eq!(prepared.execute(&[256], limits()).unwrap_err(), "entry argument exceeds its integer width");
    same(prepared.execute(&[7], limits()), reference(&p, 0, &[7], limits()));
}

#[test]
fn fresh_frames_and_registers_preserve_initial_zero_semantics() {
    let mut dirty = value("dirty", u64::MAX as u128);
    dirty.code.insert(0, Op::Imm { dst: 7, value: u128::MAX });
    let clean = function("clean", vec![Op::Assert { value: 7, expected: false, message: "dirty register".into() },
        Op::Local { dst: 0, offset: 0 }, Op::Load { dst: 1, address: 0, size: 8 },
        Op::Assert { value: 1, expected: false, message: "dirty frame".into() }, Op::Return]);
    let p = program(vec![dirty, clean]);
    let mut prepared = PreparedJit::new(&p, &limits()).unwrap();
    for _ in 0..8 { for entry in [0, 1] {
        same(prepared.execute_entry(entry, &[], limits()), reference(&p, entry, &[], limits()));
    } }
}

#[test]
fn tls_destructors_are_drained_and_failure_queues_are_discarded() {
    let root = function("register destructor", vec![
        Op::Imm { dst: 0, value: (FUNCTION_POINTER_TAG | 3) as u128 },
        Op::Imm { dst: 1, value: 7 }, Op::RegisterTlsDestructor { callback: 0, argument: 1 },
        Op::ResetThreadLocals, Op::Return]);
    let mut failed = root.clone(); failed.name = "fail with queued destructor".into();
    failed.code[3] = Op::Trap { message: "failed before teardown".into() };
    let mut callback = function("callback", vec![
        Op::Imm { dst: 0, value: (HEAP_POINTER_TAG + 32) as u128 },
        Op::Load { dst: 1, address: 0, size: 8 },
        Op::Assert { value: 1, expected: false, message: "old callback/global leaked".into() },
        Op::Imm { dst: 1, value: 1 }, Op::Store { address: 0, src: 1, size: 8 }, Op::Return]);
    callback.args = vec![Slot { offset: 0, size: 8 }]; callback.result.size = 0;
    let p = program(vec![root, failed, callback]);
    let mut prepared = PreparedJit::new(&p, &limits()).unwrap();
    for _ in 0..8 {
        assert!(prepared.execute_entry(1, &[], limits()).unwrap_err().contains("failed before teardown"));
        same(prepared.execute(&[], limits()), reference(&p, 0, &[], limits()));
    }
}

#[test]
fn code_capacity_declines_remain_correct_across_distinct_entries() {
    let p = program(vec![value("one", 1), value("two", 2)]);
    for capacity in [0, 256, 1024, Limits::default().jit_code_bytes] { for persistent in [false, true] {
        let run = || Limits { jit_code_bytes: capacity, jit_persistent_registers: persistent, ..limits() };
        let mut prepared = PreparedJit::new(&p, &run()).unwrap();
        for entry in [0, 1, 0, 1] {
            let actual = same(prepared.execute_entry(entry, &[], run()), reference(&p, entry, &[], run()));
            assert!(actual.jit_bytes <= capacity);
        }
    } }
}
