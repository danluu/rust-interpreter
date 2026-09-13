//! Test-only census of unchanged x9 bits that still equal exact local bytes.
//! This observer never substitutes a load or emits an instruction.
use super::*;

#[derive(Debug, serde::Serialize)]
pub(super) struct Hit {
    pub pc: usize,
    pub origin_pc: usize,
    pub origin: &'static str,
    pub offset: usize,
}

struct Snapshot { offset: usize, pc: usize, origin: &'static str }

#[derive(Default)]
pub(super) struct State {
    enabled: bool,
    snapshots: Vec<Snapshot>,
    pub hits: Vec<Hit>,
}

/// Only these reviewed straight-line integer encodings can preserve x9.
/// Unknown words and every control transfer conservatively invalidate it.
fn preserves_x9(word: u32) -> bool {
    let rd = word & 31;
    if word == 0xd503201f { return true; } // NOP
    // ADD/SUB immediate or shifted/extended register; logical shifted register.
    if word & 0x1f000000 == 0x11000000
        || matches!(word & 0x1f000000, 0x0a000000 | 0x0b000000) {
        return rd != 9;
    }
    // Move-wide, bitfield, extract: their sole GPR destination is Rd.
    if matches!(word & 0x1f800000, 0x12800000 | 0x13000000 | 0x13800000) {
        return rd != 9;
    }
    // Scalar unsigned-offset loads/stores have no base writeback. Every
    // nonzero opc is conservatively a load, including sign-extending forms.
    if word & 0x3b000000 == 0x39000000 && word & 0x04000000 == 0 {
        return (word >> 22) & 3 == 0 || rd != 9;
    }
    // Scalar offset LDP/STP: exclude pre/post-index modes and SIMD encodings.
    if word & 0x3b800000 == 0x29000000 && word & 0x04000000 == 0 {
        return word & (1 << 22) == 0 || (rd != 9 && (word >> 10) & 31 != 9);
    }
    false
}

impl State {
    pub fn new(enabled: bool) -> Self { Self { enabled, ..Self::default() } }
    pub fn observe_word(&mut self, word: u32) {
        if self.enabled && !preserves_x9(word) { self.snapshots.clear(); }
    }
    pub fn invalidate(&mut self, offset: Option<usize>, size: usize) {
        if !self.enabled || size == 0 { return; }
        let Some(offset) = offset else { self.snapshots.clear(); return; };
        let end = offset.checked_add(size).expect("proved frame range");
        self.snapshots.retain(|s| s.offset >= end || offset >= s.offset + 8);
    }
    pub fn capture(&mut self, pc: usize, local: Option<usize>, size: usize, origin: &'static str) {
        if !self.enabled || size != 8 { return; }
        let Some(offset) = local else { return; };
        self.snapshots.retain(|s| s.offset != offset);
        if self.snapshots.len() == 16 { self.snapshots.remove(0); }
        self.snapshots.push(Snapshot { offset, pc, origin });
    }
    pub fn load(&mut self, pc: usize, local: Option<usize>, size: usize, already_forwarded: bool) {
        if !self.enabled || size != 8 || already_forwarded { return; }
        let Some(offset) = local else { return; };
        if let Some(s) = self.snapshots.iter().find(|s| s.offset == offset) {
            self.hits.push(Hit { pc, origin_pc: s.pc, origin: s.origin, offset });
        }
    }
}

#[test]
fn scratch_classifier_rejects_clobbers_flow_unknown_and_writeback() {
    for register in 0..32 {
        for word in [0x91000400, 0xd2800000, 0xaa0003e0, 0xd340fc00,
                     0x8b010000, 0xf9400000, 0xb9800000, 0x39c00000] {
            assert_eq!(preserves_x9(word | register), register != 9, "{word:x} r{register}");
        }
        assert!(preserves_x9(0xf9000000 | register));
    }
    for word in [0x54000000, 0x14000000, 0x94000000, 0xd61f0200, 0xd65f03c0,
                 0, 0xffffffff, 0x38401569, 0x38001529, 0xa8c13569, 0xa8813520] {
        assert!(!preserves_x9(word), "{word:x}");
    }
    assert!(preserves_x9(0xa9007d69)); // STP x9,xzr,[x11], no writeback
    assert!(!preserves_x9(0xa940256a)); // LDP x10,x9,[x11]
    assert!(preserves_x9(0xa940296b)); // LDP x11,x10,[x11], offset
}

#[test]
fn scratch_snapshots_require_exact_bytes_and_survive_only_reviewed_instructions() {
    let mut state = State::new(true);
    state.capture(1, Some(8), 8, "Copy");
    state.observe_word(0xf9000169); // write x9 to a prechecked local range
    state.observe_word(0x9100402b); // address calculation in x11
    state.load(3, Some(8), 8, false);
    assert_eq!(state.hits.len(), 1);
    state.load(4, Some(8), 8, true);
    state.load(4, Some(8), 4, false);
    state.load(4, Some(9), 8, false);
    state.invalidate(Some(16), 8);
    state.load(5, Some(8), 8, false);
    assert_eq!(state.hits.len(), 2);
    state.invalidate(Some(15), 1);
    state.load(6, Some(8), 8, false);
    assert_eq!(state.hits.len(), 2);
    state.capture(7, Some(8), 8, "Load");
    state.observe_word(0x91000429); // x9 overwritten
    state.load(8, Some(8), 8, false);
    state.capture(9, Some(8), 8, "Store");
    state.invalidate(None, 0);
    state.load(10, Some(8), 8, false);
    assert_eq!(state.hits.len(), 3);
    state.invalidate(None, 1);
    state.load(11, Some(8), 8, false);
    assert_eq!(state.hits.len(), 3);
}

#[test]
fn scratch_observer_is_bounded_disabled_by_default_and_does_not_emit() {
    let mut disabled = State::default();
    disabled.capture(0, Some(8), 8, "Copy");
    disabled.load(1, Some(8), 8, false);
    assert!(disabled.snapshots.is_empty() && disabled.hits.is_empty());
    let mut state = State::new(true);
    for offset in (0..256).step_by(8) { state.capture(offset, Some(offset), 8, "Store"); }
    assert_eq!(state.snapshots.len(), 16);
    state.load(300, Some(0), 8, false); assert!(state.hits.is_empty());
    state.load(301, Some(248), 8, false); assert_eq!(state.hits.len(), 1);
    state.observe_word(0x54000000); assert!(state.snapshots.is_empty());
}

#[test]
fn scratch_copy_value_survives_virtual_pointer_redefinition_without_word_changes() {
    let program = Program { version: crate::VERSION, target: "aarch64-apple-darwin".into(),
        entry: 0, data: vec![0;16], statics: vec![], thread_locals: vec![],
        functions: vec![Function { name: "scratch copy fixture".into(), frame_size:64, frame_align:16,
            registers:8, args:vec![crate::Slot {offset:8,size:8}], result:crate::Slot {offset:0,size:8},
            code:vec![Op::Local {dst:0,offset:8}, Op::Local {dst:1,offset:16},
                Op::Copy {dst:1,src:0,size:8}, Op::Local {dst:0,offset:24},
                Op::Load {dst:2,address:1,size:8}, Op::Local {dst:3,offset:0},
                Op::Store {address:3,src:2,size:8}, Op::Return] }] };
    crate::validate(&program).unwrap();
    let plain = Jit::new_resumable(&program, false, MAX_CODE_BYTES, true).unwrap();
    let mut observer = Jit::new_resumable(&program, false, MAX_CODE_BYTES, true).unwrap();
    observer.observe_scratch_locals = true;
    let f = &program.functions[0];
    let a = plain.emit_function_inner(f, MAX_CODE_BYTES/4, 0, None).unwrap().unwrap();
    let b = observer.emit_function_inner(f, MAX_CODE_BYTES/4, 0, None).unwrap().unwrap();
    assert_eq!(a.words, b.words);
    assert_eq!(a.resumes, b.resumes);
    assert_eq!(a.operations, b.operations);
    assert!(a.scratch_hits.is_empty());
    assert_eq!(b.scratch_hits.len(), 1);
    let hit = &b.scratch_hits[0];
    assert_eq!((hit.pc, hit.origin_pc, hit.origin, hit.offset), (4, 2, "Copy", 16));
    assert!(plain.code.is_none() && observer.code.is_none());
    assert_eq!(plain.bytes + observer.bytes, 0);
}
