//! Encode counts proven by the existing region facts; keep logical ops intact.
use super::*;

impl Assembler<'_> {
    pub(super) fn immediate_shift_amount(&self, op: Binary, bits: u8, rhs: Reg) -> Option<u8> {
        let eligible = match op {
            Binary::Shl | Binary::Shr => matches!(bits, 8 | 16 | 32 | 64),
            Binary::RotateLeft | Binary::RotateRight => matches!(bits, 32 | 64),
            _ => false,
        };
        if !eligible { return None; }
        let Some(Fact::Imm(value)) = self.facts.get(&rhs) else { return None; };
        Some((value & u128::from(bits - 1)) as u8)
    }

    /// x9 contains the masked operand. The caller applies final width masking
    /// and writes value/zero overflow in the original order.
    pub(super) fn immediate_shift(&mut self, op: Binary, bits: u8, signed: bool, count: u8) {
        debug_assert!(count < bits && bits <= 64);
        if matches!(op, Binary::Shr) && signed { self.sign(9, bits); }
        if count == 0 { return; }
        let registers = (9 << 5) | 9;
        match op {
            Binary::Shl => self.emit(0xd3400000 | (u32::from(64 - count) << 16)
                | (u32::from(63 - count) << 10) | registers), // UBFM / LSL
            Binary::Shr => self.emit((if signed { 0x93400000 } else { 0xd3400000 })
                | (u32::from(count) << 16) | (63 << 10) | registers), // SBFM/UBFM
            Binary::RotateLeft | Binary::RotateRight => {
                debug_assert!(matches!(bits, 32 | 64));
                let right = if matches!(op, Binary::RotateLeft) { bits - count } else { count };
                self.emit((if bits == 64 { 0x93c00000 } else { 0x13800000 })
                    | (9 << 16) | (u32::from(right) << 10) | registers); // EXTR / ROR
            }
            _ => unreachable!("only proven immediate shifts reach this emitter"),
        }
    }
}

#[cfg(test)]
#[path = "immediate_shifts_tests.rs"]
mod tests;
