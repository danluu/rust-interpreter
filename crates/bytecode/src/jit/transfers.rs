//! Memmove within a native region; no guest storage or host ABI transition.
use super::resumable::Cond;
use super::*;

pub(super) fn supported(op: &Op) -> bool {
    matches!(op, Op::CopyDynamic { .. } | Op::Copy { size: 129.., .. })
}

impl Assembler<'_> {
    pub(super) fn copy_transfer(&mut self, op: &Op) -> Result<(), EmitError> {
        // Read every input before effects. usize conversion intentionally uses
        // the low half, matching Memory::copy's current bytecode contract.
        match *op {
            Op::CopyDynamic { dst, src, size } => {
                self.get(11, src, false);
                self.get(12, dst, false);
                self.get(10, size, false);
                self.local_values.clear();
            }
            Op::Copy { dst, src, size } => {
                self.get(11, src, false);
                self.get(12, dst, false);
                self.imm(10, size as u64);
                self.invalidate_local_memory(self.local_range(dst, size), size);
            }
            _ => unreachable!("unsupported native transfer"),
        }
        self.cmp(10, 31);
        let empty = self.words.len();
        self.emit(0x54000000 | Cond::Eq as u32);
        // Source then destination, complete ranges before any byte is touched.
        self.dynamic_read_address(11, 10);
        self.dynamic_address(12, 10, true);
        self.copy_prechecked()?;
        self.patch_conditional(empty, self.words.len())?;
        Ok(())
    }

    /// Memmove complete prechecked ranges x11 -> x12, byte count in x10.
    /// Scratch x9/x13/x14 only; preserve call targets, cursors and budgets.
    /// Shared with ABI copies after their original ordered address checks.
    pub(super) fn copy_prechecked(&mut self) -> Result<(), EmitError> {
        self.cmp(12, 11);
        let equal = self.words.len();
        self.emit(0x54000000 | Cond::Eq as u32);
        let forward = self.words.len();
        self.emit(0x54000000 | Cond::Lo as u32);
        // When dst > src, walk backwards. This is also correct for disjoint
        // ranges or distinct arenas. Proven host extents cannot wrap on add.
        for address in [11, 12] {
            self.three(0x8b000000, address, address, 10);
        }
        let backward_exits = self.copy_direction(false)?;
        let forward_start = self.words.len();
        let forward_exits = self.copy_direction(true)?;
        let done = self.words.len();
        self.patch_conditional(forward, forward_start)?;
        for at in [equal]
            .into_iter()
            .chain(backward_exits)
            .chain(forward_exits)
        {
            self.patch_conditional(at, done)?;
        }
        Ok(())
    }

    /// x11/x12 are checked source/destination, x10 is the remaining count.
    /// Only x9/x13/x14 are scratch. No persistent/cache/ABI register is changed.
    /// Load each whole pair before storing it, so displacements smaller than
    /// sixteen bytes still have memmove semantics in either direction.
    fn copy_direction(&mut self, forward: bool) -> Result<[usize; 2], EmitError> {
        self.imm(14, 16);
        self.cmp(10, 14);
        let short = self.words.len();
        self.emit(0x54000000 | Cond::Lo as u32);
        let pairs = self.words.len();
        // ldp/stp x9,x13,[x11/x12],#16 (forward), or [x11/x12,#-16]!
        let (load, store) = if forward {
            (0xa8c10000, 0xa8810000)
        } else {
            (0xa9ff0000, 0xa9bf0000)
        };
        self.emit(load | (13 << 10) | (11 << 5) | 9);
        self.emit(store | (13 << 10) | (12 << 5) | 9);
        self.sub_imm(10, 10, 16);
        self.cmp(10, 14);
        let more_pairs = self.words.len();
        self.emit(0x54000000 | Cond::Hs as u32);
        let tail = self.words.len();
        self.cmp(10, 31);
        let exhausted = self.words.len();
        self.emit(0x54000000 | Cond::Eq as u32);
        let bytes = self.words.len();
        // ldrb/strb w9,[x11/x12],#1, or [x11/x12,#-1]!
        let (load, store) = if forward {
            (0x38401400, 0x38001400)
        } else {
            (0x385ffc00, 0x381ffc00)
        };
        self.emit(load | (11 << 5) | 9);
        self.emit(store | (12 << 5) | 9);
        self.emit(0xf1000000 | (1 << 10) | (10 << 5) | 10); // subs x10,x10,#1
        let more_bytes = self.words.len();
        self.emit(0x54000000 | Cond::Ne as u32);
        // The final SUBS established zero; this always-taken conditional exit
        // allows all forward targets to use the checked B.cond relocation API.
        let done = self.words.len();
        self.emit(0x54000000 | Cond::Eq as u32);
        self.patch_conditional(short, tail)?;
        self.patch_conditional(more_pairs, pairs)?;
        self.patch_conditional(more_bytes, bytes)?;
        Ok([exhausted, done])
    }
}

#[cfg(all(test, target_arch = "aarch64", target_os = "macos"))]
#[path = "transfers_tests.rs"]
mod tests;
