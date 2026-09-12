"""Inject the isolated x22 budget ABI after reconstructing aggregate relocation."""
import shutil

from build_relocation import HERE, replace


def inject(source):
    jit = source/'crates/bytecode/src/jit.rs'
    resume = jit.parent/'jit/resumable.rs'
    values = jit.parent/'jit/values.rs'
    replace(resume, 'const MAX_ENTRY_BYTES: usize', '''// Live across every internal resumable edge. The external prologue saves
// the host value; every VM exit publishes the guest budget before restoring it.
// Guest persistent pairs remain x23/x24, x25/x26 and x27/x28.
pub(super) const BUDGET_REGISTER: u32 = 22;

const MAX_ENTRY_BYTES: usize''')
    replace(jit, '''                a.emit(0xf9400269); // ldr x9, [x19]
                a.imm(10, (pc - start) as u64);
                a.cmp(9, 10);''', '''                let budget = if resumable { resumable::BUDGET_REGISTER } else { 9 };
                if !resumable { a.emit(0xf9400269); } // ordinary Cursor.remaining
                a.imm(10, (pc - start) as u64);
                a.cmp(budget, 10);''')
    replace(jit, '''                a.three(0xcb000000, 9, 9, 10);
                a.emit(0xf9000269); // str x9, [x19]''', '''                a.three(0xcb000000, budget, budget, 10);
                if !resumable { a.emit(0xf9000269); }''')
    replace(values, '''        if self.resumable { self.resumable_current_frame(); }
        let resume = self.words.len();''', '''        if self.resumable {
            self.resumable_current_frame();
            self.resumable_load_budget();
        }
        // Native callees inherit x22; only external Rust entries load memory.
        let resume = self.words.len();''')
    replace(jit, '        if self.resumable { self.resumable_save_memory(); }', '''        if self.resumable {
            self.resumable_save_memory();
            self.resumable_save_budget();
        }''')
    replace(resume, '''        a.load64(9, 19, state::REMAINING);
        a.cmp(9, 31);''', '''        a.cmp(BUDGET_REGISTER, 31);''')
    replace(resume, '''        self.load64(9, 19, state::REMAINING);
        self.sub_imm(9, 9, 1);
        self.store64(9, 19, state::REMAINING);''', '''        self.sub_imm(BUDGET_REGISTER, BUDGET_REGISTER, 1);''')
    replace(resume, '    pub(super) fn resumable_save_memory(&mut self) {', '''    pub(super) fn resumable_load_budget(&mut self) {
        self.load64(BUDGET_REGISTER, 19, state::REMAINING);
    }
    pub(super) fn resumable_save_budget(&mut self) {
        self.store64(BUDGET_REGISTER, 19, state::REMAINING);
    }
    pub(super) fn resumable_save_memory(&mut self) {''')
    # Preflight x17 is dead before any checked address/argument-copy helper.
    for old, new in [
        ('self.three(0xab000000, 22, 12, 10);', 'self.three(0xab000000, 17, 12, 10);'),
        ('self.cmp(22, 10);', 'self.cmp(17, 10);'),
        ('self.lsl_imm(13, 22, 4);', 'self.lsl_imm(13, 17, 4);'),
        # After argument copies, only zero_range, get, frame stores and cursor
        # increments intervene before mov x0,x17. Their scratch excludes x17.
        ('self.three(0x8b000000, 22, 0, 9);', 'self.three(0x8b000000, 17, 0, 9);'),
        ('self.mov(11, 22);', 'self.mov(11, 17);'),
        ('self.three(0x8b000000, 12, 22, 12);', 'self.three(0x8b000000, 12, 17, 12);'),
        ('self.mov(0, 22);', 'self.mov(0, 17);'),
    ]:
        replace(resume, old, new)
    replace(resume, '        self.load64(22, 20, frame::REGISTER_BASE);\n', '')
    replace(resume, '''        self.mov(3, 21);
        self.store64(22, 19, state::REGISTER_LEN);''', '''        self.mov(3, 21);
        // The checked result copy can clobber x17. Frame metadata is private
        // host storage and unchanged by that copy; read it only after success.
        self.load64(17, 20, frame::REGISTER_BASE);
        self.store64(17, 19, state::REGISTER_LEN);''')
    tests = jit.parent/'jit/resumable_tests.rs'
    with tests.open('a') as stream:
        stream.write('\n#[path="budget_register_tests.rs"]\nmod budget_register;\n')
    shutil.copy2(HERE/'budget_register_tests.rs', tests.with_name('budget_register_tests.rs'))
