use super::*;
use crate::{Function, Op, Slot, heap};

struct Fixture {
    program: Program,
    memory: Memory,
    registers: Vec<u128>,
    frames: Frames,
    register_bytes: usize,
    limits: Limits,
}

impl Fixture {
    fn new() -> Self {
        let functions = [(32, 16, 4), (48, 32, 6), (16, 16, 3)]
            .into_iter()
            .enumerate()
            .map(|(id, (frame_size, frame_align, registers))| Function {
                name: format!("frame-{id}"),
                frame_size,
                frame_align,
                registers,
                args: vec![],
                result: Slot { offset: 0, size: 0 },
                code: vec![
                    Op::Imm { dst: 0, value: 0 },
                    if id < 2 {
                        Op::Call {
                            function: id + 1,
                            args: vec![],
                            destination: 0,
                        }
                    } else {
                        Op::Jump { target: 0 }
                    },
                    Op::Return,
                ],
            })
            .collect();
        let program = Program {
            version: crate::VERSION,
            target: "aarch64-apple-darwin".into(),
            entry: 0,
            functions,
            data: vec![0; 32],
            statics: vec![0; 16],
            thread_locals: vec![],
        };
        crate::validate(&program).unwrap();
        let limits = Limits {
            memory: 4096,
            frames: 8,
            ..Limits::default()
        };
        let mut memory = Memory {
            bytes: vec![0; 64].into(),
            heap: heap::Heap::with_statics(&program.statics, limits.allocations),
            limit: limits.memory,
            readonly_end: 32,
            peak: 83,
            auxiliary_bytes: 3,
        };
        memory.bytes.prepare(512).unwrap();
        let mut frames = Frames::from(Frame {
            function: 0,
            pc: 1,
            base: 32,
            register_base: 0,
            return_address: 0,
            return_value: false, tls_callback: true,
        });
        frames.prepare(8).unwrap();
        Self {
            program,
            memory,
            registers: vec![0; 64],
            frames,
            register_bytes: 64,
            limits,
        }
    }

    fn boundary(&self) -> Boundary {
        Boundary::new(
            &self.program,
            &self.memory,
            &self.registers,
            &self.frames,
            self.register_bytes,
            100,
            &self.limits,
            Capacity {
                memory: 512,
                registers: 64,
                frames: 8,
            },
            std::ptr::null_mut(),
        )
        .unwrap()
    }

    fn finish(&mut self, boundary: Boundary, state: State, status: Status) -> Result<Run, String> {
        boundary.finish(
            &self.program,
            &mut self.memory,
            &self.registers,
            &mut self.frames,
            &mut self.register_bytes,
            state,
            status,
        )
    }

    fn write_children(&mut self) {
        let pointer = self.frames.prepared_mut_ptr();
        // SAFETY: exclusive initialized backing. These complete typed writes
        // model a native entry's descriptors; no guest code is executed here.
        unsafe {
            (*pointer).pc = 2;
            pointer.add(1).write(Frame {
                function: 1,
                pc: 2,
                base: 64,
                register_base: 4,
                return_address: 32,
                return_value: false, tls_callback: false,
            });
            pointer.add(2).write(Frame {
                function: 2,
                pc: 1,
                base: 112,
                register_base: 10,
                return_address: 64,
                return_value: false, tls_callback: false,
            });
        }
    }
}

#[test]
fn descendant_and_ancestor_continuations_publish_the_actual_frame() {
    let mut f = Fixture::new();
    let boundary = f.boundary();
    let mut state = boundary.state();
    f.write_children();
    state.remaining = 90;
    state.calls = 2;
    state.frame_len = 3;
    state.register_len = 13;
    state.memory_len = 128;
    state.peak_linear = 128;
    let run = f.finish(boundary, state, Status::Continue).unwrap();
    assert_eq!(
        run.exit,
        Exit::Resume(Position {
            depth: 3,
            function: 2,
            pc: 1
        })
    );
    assert_eq!((run.instructions, run.calls, run.returns), (10, 2, 0));
    assert_eq!(
        (f.frames.len(), f.register_bytes, f.memory.bytes.len()),
        (3, 208, 128)
    );
    assert_eq!(f.memory.peak, 147);
    f.frames.last_mut().unwrap().pc += 1; // one VM step in the descendant

    let boundary = f.boundary();
    let mut state = boundary.state();
    state.remaining = 98;
    state.returns = 2;
    state.frame_len = 1;
    state.register_len = 4;
    state.memory_len = 64;
    let run = f.finish(boundary, state, Status::Continue).unwrap();
    assert_eq!(
        run.exit,
        Exit::Resume(Position {
            depth: 1,
            function: 0,
            pc: 2
        })
    );
    assert_eq!((run.instructions, run.calls, run.returns), (2, 0, 2));
    assert_eq!(
        (f.frames.len(), f.register_bytes, f.memory.bytes.len()),
        (1, 64, 64)
    );
    assert_eq!(f.memory.peak, 147);
    assert!(f.frames.last().unwrap().tls_callback); // root/TLS Return stays in VM
    assert_eq!(f.frames.prepared_frame(2).unwrap().pc, 2);
}

#[test]
fn unchanged_pc_with_progress_is_distinct_from_a_zero_progress_decline() {
    for consumed in [0, 1, 100] {
        let mut f = Fixture::new();
        let boundary = f.boundary();
        let mut state = boundary.state();
        state.remaining -= consumed;
        let run = f.finish(boundary, state, Status::Continue).unwrap();
        assert_eq!(run.instructions, consumed);
        assert_eq!(
            run.exit,
            if consumed == 0 {
                Exit::Declined
            } else {
                Exit::Resume(Position {
                    depth: 1,
                    function: 0,
                    pc: 1,
                })
            }
        );
    }
}

#[test]
fn exhausted_one_past_code_continuation_and_fault_have_distinct_outcomes() {
    let mut f = Fixture::new();
    let boundary = f.boundary();
    let mut state = boundary.state();
    state.remaining = 0;
    f.frames.last_mut().unwrap().pc = f.program.functions[0].code.len();
    let run = f.finish(boundary, state, Status::Continue).unwrap();
    assert_eq!(
        run.exit,
        Exit::Resume(Position {
            depth: 1,
            function: 0,
            pc: 3
        })
    );
    assert_eq!(run.instructions, 100);

    let boundary = f.boundary();
    let mut state = boundary.state();
    state.remaining = 99;
    // A Call can reserve memory and fail copying an argument before pushing.
    state.memory_len = 160;
    state.peak_linear = 160;
    let run = f.finish(boundary, state, Status::Fault(123)).unwrap();
    assert_eq!(run.exit, Exit::Fault(123));
    assert_eq!(run.instructions, 1);
    assert_eq!(
        (f.frames.len(), f.register_bytes, f.memory.bytes.len()),
        (1, 64, 160)
    );
    assert_eq!(f.memory.peak, 179);
}

#[test]
fn malformed_cursors_never_publish_a_partial_extent() {
    let mutations: &[fn(&mut State)] = &[
        |s| s.remaining = 101,
        |s| s.frame_len = 0,
        |s| s.frame_len = 9,
        |s| s.memory_len = 513,
        |s| s.peak_linear = 513,
        |s| s.peak_linear = 63,
        |s| s.memory_len = 65,
        |s| s.register_len = usize::MAX,
        |s| s.calls = u64::MAX,
        |s| {
            s.calls = u64::MAX;
            s.returns = 1;
        },
        |s| {
            s.calls = 2;
            s.frame_len = 3;
        }, // only one instruction consumed
        |s| s.returns = 2,
    ];
    for mutation in mutations {
        let mut f = Fixture::new();
        let boundary = f.boundary();
        let mut state = boundary.state();
        state.remaining -= 1;
        mutation(&mut state);
        assert!(
            f.finish(boundary, state, Status::Continue).is_err(),
            "{state:?}"
        );
        assert_eq!(
            (
                f.frames.len(),
                f.register_bytes,
                f.memory.bytes.len(),
                f.memory.peak
            ),
            (1, 64, 64, 83)
        );
    }
}

#[test]
fn malformed_descriptors_and_changes_without_progress_are_rejected() {
    let mutations: &[fn(&mut Frame)] = &[
        |f| f.function = usize::MAX,
        |f| f.pc = 4,
        |f| f.base = 0,
        |f| f.base = 16, // inside read-only prefix
        |f| f.base = 33,
        |f| f.base = usize::MAX - 15,
        |f| f.register_base = usize::MAX,
        |f| f.register_base = 1,
    ];
    for mutation in mutations {
        let mut f = Fixture::new();
        let boundary = f.boundary();
        let mut state = boundary.state();
        state.remaining -= 1;
        mutation(f.frames.last_mut().unwrap());
        assert!(f.finish(boundary, state, Status::Continue).is_err());
        assert_eq!(
            (
                f.frames.len(),
                f.register_bytes,
                f.memory.bytes.len(),
                f.memory.peak
            ),
            (1, 64, 64, 83)
        );
    }
    for change in 0..5 {
        let mut f = Fixture::new();
        let boundary = f.boundary();
        let mut state = boundary.state();
        let mut status = Status::Continue;
        match change {
            0 => f.frames.last_mut().unwrap().pc += 1,
            1 => f.frames.last_mut().unwrap().tls_callback = false,
            2 => {
                state.memory_len = 65;
                state.peak_linear = 65;
            }
            3 => state.peak_linear += 1,
            4 => status = Status::Fault(1),
            _ => unreachable!(),
        }
        assert!(f.finish(boundary, state, status).is_err());
        assert_eq!(
            (
                f.frames.len(),
                f.register_bytes,
                f.memory.bytes.len(),
                f.memory.peak
            ),
            (1, 64, 64, 83)
        );
    }
}

#[test]
fn preparation_capacity_cannot_replace_guest_limits_or_storage_identity() {
    for limit in [0, 1] {
        let mut f = Fixture::new();
        if limit == 0 {
            f.limits.frames = 1;
        } else {
            f.limits.memory = 180;
        }
        let boundary = f.boundary();
        let mut state = boundary.state();
        f.write_children();
        state.remaining = 90;
        state.calls = 2;
        state.frame_len = 3;
        state.register_len = 13;
        state.memory_len = 128;
        state.peak_linear = 128;
        assert!(f.finish(boundary, state, Status::Continue).is_err());
        assert_eq!(
            (
                f.frames.len(),
                f.register_bytes,
                f.memory.bytes.len(),
                f.memory.peak
            ),
            (1, 64, 64, 83)
        );
    }
    let mut f = Fixture::new();
    let boundary = f.boundary();
    let state = boundary.state();
    let replacement = f.registers.clone();
    assert_ne!(f.registers.as_ptr(), replacement.as_ptr());
    f.registers = replacement;
    assert!(
        f.finish(boundary, state, Status::Continue)
            .unwrap_err()
            .contains("backing changed")
    );
    assert_eq!(
        (
            f.frames.len(),
            f.register_bytes,
            f.memory.bytes.len(),
            f.memory.peak
        ),
        (1, 64, 64, 83)
    );
}

#[test]
fn value_return_publication_checks_caller_register_width_and_tag_context() {
    let mut f=Fixture::new();f.program.version=crate::scalar_abi::SCALAR_VERSION;
    f.program.functions[1].result.size=8;
    f.memory.bytes.resize(128,0);f.register_bytes=10*16;
    f.frames.push(Frame{function:1,pc:0,base:64,register_base:4,return_address:3,
        tls_callback:false,return_value:true});
    let valid=|f:&Fixture|Boundary::new(&f.program,&f.memory,&f.registers,&f.frames,f.register_bytes,100,&f.limits,
        Capacity{memory:512,registers:64,frames:8},std::ptr::null_mut()).is_ok();
    assert!(valid(&f));
    f.frames[1].return_address=4;assert!(!valid(&f));f.frames[1].return_address=3;
    f.frames[1].tls_callback=true;assert!(!valid(&f));f.frames[1].tls_callback=false;
    f.program.functions[1].result.size=0;assert!(!valid(&f));f.program.functions[1].result.size=8;
    f.program.version=crate::VERSION;assert!(!valid(&f));f.program.version=crate::scalar_abi::SCALAR_VERSION;
    f.frames.pop();f.register_bytes=4*16;f.memory.bytes.truncate(64);
    f.frames[0].return_value=true;assert!(!valid(&f));
}
