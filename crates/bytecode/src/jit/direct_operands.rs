//! Read existing native values directly for modular arithmetic and bitwise ops.
use super::*;

impl Assembler<'_> {
    fn low_operand(&mut self, scratch: u32, reg: Reg) -> u32 {
        let native = match self.facts.get(&reg).copied() {
            Some(Fact::Physical { lo }) => Some(lo),
            Some(Fact::Cached { lo, .. }) => {
                self.cache_recent = (lo - 5) as usize;
                Some(lo)
            }
            Some(Fact::Imm(value)) if value as u64 == 0 => Some(31),
            // An immediate or local fact overrides an assigned register whose
            // stored value may not have been updated yet.
            Some(_) => None,
            None => self.assigned_pair(reg).inspect(|&lo| {
                self.facts.insert(reg, Fact::Physical { lo });
            }),
        };
        if let Some(native) = native {
            if !self.defined.contains(&reg) { self.live_in.insert(reg); }
            native
        } else {
            self.get(scratch, reg, false);
            scratch
        }
    }

    pub(super) fn direct_binary(&mut self, dst: Reg, overflow: Reg,
        op: Binary, a: Reg, b: Reg, bits: u8) -> bool {
        if !matches!(bits, 8 | 16 | 32 | 64) { return false; }
        let unobserved = self.reads[overflow as usize].is_none();
        let opcode = match op {
            Binary::Add if unobserved => 0x8b000000,
            Binary::Sub if unobserved => 0xcb000000,
            Binary::Mul if unobserved => 0x9b007c00,
            Binary::And => 0x8a000000,
            Binary::Or => 0xaa000000,
            Binary::Xor => 0xca000000,
            _ => return false,
        };
        // Neither read changes any source native register. Fetch both before
        // publishing outputs; scratch x9/x10 do not overlap either value bank.
        let left = self.low_operand(9, a);
        let right = self.low_operand(10, b);
        self.three(opcode, 9, left, right);
        // Low n bits of these modular operations depend only on the low n
        // input bits. One result mask therefore replaces both input masks.
        // Observed arithmetic overflow retains the original checked path.
        self.mask(9, bits);
        self.put(dst, 9, 31);
        self.put(overflow, 31, 31); // preserve value-before-overflow alias order
        true
    }
}

#[cfg(test)]
#[path = "direct_operands_tests.rs"]
mod tests;
