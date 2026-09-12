use rust_interp_bytecode::{Engine, Limits, execute_with_engine};
#[path = "common/call_copy_cases.rs"]
mod cases;

#[test]
fn call_arguments_preserve_explicit_values_faults_and_instruction_budgets() {
    for case in cases::cases() {
        rust_interp_bytecode::validate(&case.program).unwrap();
        let mut expected_steps = None;
        for engine in [Engine::Interpreter, Engine::Jit] {
            let result = execute_with_engine(&case.program, &[], Limits::default(), engine);
            assert_eq!(
                result.as_ref().map(|r| r.value).map_err(String::as_str),
                case.expected,
                "{} / {engine:?}",
                case.name
            );
            if let Ok(result) = result {
                if let Some(steps) = expected_steps {
                    assert_eq!(result.instructions, steps);
                }
                expected_steps = Some(result.instructions);
                for budget in 0..=result.instructions {
                    let got = execute_with_engine(
                        &case.program,
                        &[],
                        Limits {
                            instructions: budget,
                            ..Limits::default()
                        },
                        engine,
                    );
                    if budget < result.instructions {
                        assert_eq!(
                            got.unwrap_err(),
                            "interpreter instruction limit exceeded",
                            "{} / {engine:?} / {budget}",
                            case.name
                        );
                    } else {
                        assert_eq!(got.unwrap().value, case.expected.unwrap());
                    }
                }
            }
        }
    }
}

#[test]
fn argument_failures_keep_their_order_against_frame_and_memory_limits() {
    let mut case = cases::cases()
        .into_iter()
        .find(|c| c.name == "invalid-argument-before-depth-error")
        .unwrap();
    case.program.functions[1].frame_size = 256;
    case.program.functions[1].registers = 16;
    for engine in [Engine::Interpreter, Engine::Jit] {
        for (memory, expected) in [
            (128, "interpreter memory limit exceeded"),
            (384, "interpreter working-memory limit exceeded"),
            (4096, "invalid guest memory access"),
        ] {
            let got = execute_with_engine(
                &case.program,
                &[],
                Limits {
                    memory,
                    frames: 1,
                    ..Limits::default()
                },
                engine,
            );
            assert_eq!(got.unwrap_err(), expected, "{engine:?} / {memory}");
        }
    }
}
