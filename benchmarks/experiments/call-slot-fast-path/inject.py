"""Apply only the guarded Call argument experiment to the integrated source."""
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent


def replace(path, old, new):
    text = path.read_text()
    if text.count(old) != 1: raise RuntimeError('changed injection anchor: '+old[:100])
    path.write_text(text.replace(old,new))


def inject(source):
    jit = source/'crates/bytecode/src/jit.rs'
    resume = source/'crates/bytecode/src/jit/resumable.rs'
    replace(jit, 'mod resumable;', 'mod resumable;\nmod call_slots;')
    replace(jit, '    resumable: Option<resumable::Entries>,',
        '    resumable: Option<resumable::Entries>,\n    #[cfg(test)]\n    disable_call_slot_hints: bool,')
    replace(jit, 'resumable: None,', 'resumable: None,\n            #[cfg(test)]\n            disable_call_slot_hints: false,')
    replace(jit, '        let fills = local_fills(f);', '''        let fills = local_fills(f);
        let slots = if resumable { call_slots::collect(f, self.program) } else { std::collections::BTreeMap::new() };
        #[cfg(test)]
        let slots = if self.disable_call_slot_hints { std::collections::BTreeMap::new() } else { slots };''')
    replace(jit, 'self.emit_resumable_transition(f, pc, &reads, values.as_ref())?',
        'self.emit_resumable_transition(f, pc, &reads, values.as_ref(), slots.get(&pc).map(Vec::as_slice))?')
    replace(resume, '''        values: Option<&'b values::Allocation>,
    ) -> Result<(Assembler<'b>, usize, usize), EmitError> {''', '''        values: Option<&'b values::Allocation>,
        slots: Option<&[Option<usize>]>,
    ) -> Result<(Assembler<'b>, usize, usize), EmitError> {''')
    replace(resume, '''                    args,
                    *destination,''', '''                    args,
                    slots,
                    *destination,''')
    replace(resume, '''        args: &[Reg],
        destination: Reg,''', '''        args: &[Reg],
        slots: Option<&[Option<usize>]>,
        destination: Reg,''')
    replace(resume, '''        for (source, slot) in args.iter().zip(&callee.args) {
            self.address(11, *source, slot.size, false);''', '''        for (index, (source, slot)) in args.iter().zip(&callee.args).enumerate() {
            self.call_argument_address(*source, slot.size, slots.and_then(|s| s.get(index).copied()).flatten())?;''')
    replace(resume, '    fn resumable_call(', '''    /// Hints never replace runtime register state. Equality with a proved
    /// current-frame range permits direct host addressing; mismatch follows
    /// the original check after the same charge, clearing and earlier copies.
    fn call_argument_address(&mut self, source: Reg, size: usize, hint: Option<usize>) -> Result<(), EmitError> {
        let Some(offset) = hint.filter(|&offset| size != 0 && offset.checked_add(size)
            .is_some_and(|end| end <= self.frame_size)) else {
            self.address(11, source, size, false);
            return Ok(());
        };
        self.get(11, source, false); // including persistent pairs / large offsets
        self.imm(12, offset as u64);
        self.three(0x8b000000, 12, 1, 12); // expected guest address, not a host pointer
        self.cmp(11, 12);
        let fast = self.words.len();
        self.emit(0x54000000 | Cond::Eq as u32);
        self.checked_address(11, size, false);
        let done = self.words.len();
        self.emit(0x14000000);
        self.patch_conditional(fast, self.words.len())?;
        self.three(0x8b000000, 11, 2, 12);
        // This local target is the next instruction appended by the caller.
        // The branch slot was emitted immediately above and has no other owner.
        self.words[done] |= branch_displacement(done, self.words.len(), 26, CodegenLimit::Jump)?;
        Ok(())
    }

    fn resumable_call(''')
    for name in ['call_slots.rs','call_slots_tests.rs']:
        shutil.copy2(HERE/name, source/'crates/bytecode/src/jit'/name)
    shutil.copy2(HERE/'slot_arguments_tests.rs',source/'crates/bytecode/src/jit/slot_arguments_tests.rs')
    with (source/'crates/bytecode/src/jit/resumable_tests.rs').open('a') as stream:
        stream.write('\n#[path="slot_arguments_tests.rs"]\nmod slot_arguments;\n')
