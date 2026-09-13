use super::*;

fn leaf(calls: usize, returns: usize) -> platform::Code {
    let reads = [None; 8];
    let mut a = Assembler { resumable: true, reads: &reads, ..Assembler::default() };
    // Same host preservation and counter lifetime as an external entry; this
    // leaf needs no guest Frame and exercises the real VM-return publication.
    a.resumable_save_host(false);
    a.mov(19, 7);
    a.resumable_load_budget();
    a.load_native_counters();
    for _ in 0..calls { assert!(a.increment_native_counter(state::CALLS)); }
    a.lower(&Op::Copy { dst: 1, src: 0, size: 128 }); // writes v0..v7
    a.lower(&Op::Unary { dst: 3, src: 2, bits: 64, op: Unary::CountOnes }); // writes v0
    a.imm(11, 0x1234);
    a.emit(0x9e670170); // guarded-range d16 cache, independent of counters
    for _ in 0..returns { assert!(a.increment_native_counter(state::RETURNS)); }
    a.mov(0, 31);
    a.return_to_vm();
    let failed = a.words.len();
    a.imm(0, Failure::Memory as u64);
    a.return_to_vm();
    for (at, kind) in std::mem::take(&mut a.failures) {
        assert!(kind == Failure::Memory);
        a.patch_conditional(at, failed).unwrap();
    }
    let mut code = platform::Code::reserve(4096).unwrap();
    code.append(&a.words).unwrap();
    code
}

#[test]
fn native_counter_lanes_wrap_without_cross_lane_or_adjacent_state_writes() {
    for (calls, returns) in [(0, 0), (1, 0), (0, 1), (3, 5)] {
        let code = leaf(calls, returns);
        for initial in [[0, 0], [u64::MAX, 7], [11, u64::MAX], [u64::MAX, u64::MAX]] {
            for start in [1, 2] { // initialized State at both mod16 alignments
                for invalid in [false, true] {
                    let mut cursor = [0xa5a5_a5a5_a5a5_a5a5u64; 16];
                    cursor[start] = 123; // budget preserved by the real epilogue
                    cursor[start + state::MEMORY_LEN / 8] = 640;
                    cursor[start + state::CALLS / 8] = initial[0];
                    cursor[start + state::RETURNS / 8] = initial[1];
                    // Repeated host entries must reload current memory, even
                    // if unrelated host code destroys every volatile vector.
                    for entry in 0..3 {
                        let mut expected = cursor;
                        expected[start + state::CALLS / 8] = cursor[start + state::CALLS / 8].wrapping_add(calls as u64);
                        expected[start + state::RETURNS / 8] = cursor[start + state::RETURNS / 8].wrapping_add(if invalid { 0 } else { returns as u64 });
                        let mut memory: Vec<u8> = (0..640).map(|i| (i * 71 + entry) as u8).collect();
                        let mut reference = memory.clone();
                        if !invalid { reference.copy_within(64..192, 256); }
                        let mut registers = [if invalid { 640 } else { 64 }, 256, 0x1234_5678_9abc_def0, 0, 0, 0, 0, 0];
                        // SAFETY: emitted code validates guest Copy bounds.
                        // Cursor, registers and memory are stable initialized
                        // owned arrays; all host writes stay in their bounds.
                        let result = unsafe { code.call(0, registers.as_mut_ptr(), 0,
                            memory.as_mut_ptr(), memory.len(), 0, std::ptr::null_mut(), 0,
                            cursor.as_mut_ptr().add(start).cast()) };
                        assert_eq!(result, if invalid { Failure::Memory as u64 } else { 0 });
                        assert_eq!(cursor, expected, "start={start}, entry={entry}, invalid={invalid}");
                        assert_eq!(memory, reference);
                        if !invalid { assert_eq!(registers[3], 32); }
                        // Change both lanes between entries; retaining stale
                        // vector values across the host boundary would fail.
                        cursor[start + state::CALLS / 8] ^= 0xfedc_ba98_7654_3210;
                        cursor[start + state::RETURNS / 8] ^= 0x0123_4567_89ab_cdef;
                    }
                }
            }
        }
    }
}

#[test]
fn native_counter_words_match_external_assembler_control_and_historical_switch() {
    let mut a = Assembler::default();
    a.load_native_counters();
    assert!(a.increment_native_counter(state::CALLS));
    assert!(a.increment_native_counter(state::RETURNS));
    assert!(!a.increment_native_counter(state::FRAME_LEN));
    a.save_native_counters();
    assert_eq!(a.words, [0x3dc00e7d, 0xd2800029, 0x9e67013e, 0x6f00e41f,
        0x4e181d3f, 0x4efe87bd, 0x4eff87bd, 0x3d800e7d]);
    let mut historical = Assembler { register_native_counters: false, ..Assembler::default() };
    historical.load_native_counters();
    assert!(!historical.increment_native_counter(state::CALLS));
    assert!(!historical.increment_native_counter(state::RETURNS));
    historical.save_native_counters();
    assert!(historical.words.is_empty());
}
