use super::*;

fn check_profiles_at_all_budgets(p: &Program) {
    let total = execute_with_engine(p, &[], Limits::default(), Engine::Interpreter)
        .map(|r| r.instructions).unwrap_or(40);
    for budget in 0..=total + 1 {
        let reference = execute_profiled(p, &[], Limits { instructions: budget, ..Limits::default() }, Engine::Interpreter);
        for persistent in [false, true] {
            let limits = || Limits { instructions: budget, jit_resumable_calls: true,
                jit_persistent_registers: persistent, ..Limits::default() };
            let actual = execute_profiled(p, &[], limits(), Engine::Jit);
            match (actual, &reference) {
                (Ok((a, ap)), Ok((b, bp))) => {
                    assert_eq!((a.value, a.instructions, a.peak_memory), (b.value, b.instructions, b.peak_memory));
                    assert_eq!(logical(&ap), logical(bp));
                    assert_eq!(logical(&ap).iter().flatten().sum::<u64>(), a.instructions);
                    let plain = execute_with_engine(p, &[], limits(), Engine::Jit).unwrap();
                    assert_eq!((plain.value, plain.instructions, plain.peak_memory), (a.value, a.instructions, a.peak_memory));
                    assert_eq!((plain.jit_resumable_calls, plain.jit_resumable_returns),
                               (a.jit_resumable_calls, a.jit_resumable_returns));
                }
                (Err(a), Err(b)) => assert_eq!(a, *b),
                (a, b) => panic!("budget {budget} persistent={persistent}: {a:?} versus {b:?}"),
            }
        }
    }
}

#[test]
fn budget_survives_internal_entries_and_profiled_fallback_at_every_step() {
    for unsupported in [false, true] {
        check_profiles_at_all_budgets(&looping_program(unsupported));
    }
    check_profiles_at_all_budgets(&recursive_program(3));
}

fn large_copy(invalid_return: bool) -> Program {
    let mut root = function(vec![
        Op::Local { dst: 0, offset: 0 },
        Op::Imm { dst: 1, value: 111 },
        Op::Store { address: 0, src: 1, size: 8 },
        if invalid_return { Op::Imm { dst: 4500, value: 0 } }
        else { Op::Local { dst: 4500, offset: 1024 } },
        Op::Call { function: 1, args: vec![0], destination: 4500 },
        Op::Return,
    ]);
    root.frame_size = 2048;
    root.registers = 5000;
    root.result = Slot { offset: 1024, size: 8 };
    let mut child = function(vec![
        Op::Local { dst: 0, offset: 0 },
        Op::Load { dst: 1, address: 0, size: 8 },
        // This read-before-definition forces large entry-register zeroing.
        binary(2, Binary::Add, 1, 5500),
        Op::Store { address: 0, src: 2, size: 8 },
        Op::Return,
    ]);
    child.frame_size = 512;
    child.registers = 6000;
    child.args = vec![Slot { offset: 0, size: 512 }];
    child.result = Slot { offset: 0, size: 512 };
    program(vec![root, child])
}

#[test]
fn large_register_zero_and_abi_copies_preserve_budget_and_callee_pointer() {
    let p = large_copy(false);
    assert_eq!(execute_with_engine(&p, &[], Limits::default(), Engine::Interpreter).unwrap().value, 111);
    check_profiles_at_all_budgets(&p);
}

#[test]
fn return_copy_fault_preserves_the_charged_budget_and_fault_order() {
    let p = large_copy(true);
    assert!(execute_with_engine(&p, &[], Limits::default(), Engine::Interpreter).is_err());
    check_profiles_at_all_budgets(&p);
}

#[test]
fn arithmetic_memory_and_assertion_exits_publish_the_same_budget() {
    for tail in [
        Op::Load { dst: 2, address: 0, size: 8 },
        binary(2, Binary::Div, 1, 0),
        Op::Assert { value: 0, expected: true, message: "budget-register assertion".into() },
    ] {
        let p = program(vec![function(vec![
            Op::Imm { dst: 0, value: 0 }, Op::Imm { dst: 1, value: 1 },
            Op::Jump { target: 3 }, tail, Op::Return,
        ])]);
        check_profiles_at_all_budgets(&p);
    }
}
