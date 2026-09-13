//! Exact counters live only for one host-to-native activation.
use super::*;
use crate::native_continuation::layout as state;

impl Assembler<'_> {
    fn native_counters_enabled(&self) -> bool {
        #[cfg(test)]
        { self.register_native_counters }
        #[cfg(not(test))]
        { true }
    }

    pub(super) fn load_native_counters(&mut self) {
        if !self.native_counters_enabled() { return; }
        // v29 holds [calls, returns]; v30/v31 hold the respective increments.
        // These caller-saved registers survive every internal edge. Existing
        // generated operations use v0..v7 and d16; no host call occurs inside
        // a resumable activation. Host reentry always reloads these registers.
        const _: () = assert!(state::CALLS % 16 == 0 && state::RETURNS == state::CALLS + 8);
        self.emit(0x3dc00000 | ((state::CALLS as u32 / 16) << 10) | (19 << 5) | 29);
        self.imm(9, 1);
        self.emit(0x9e670000 | (9 << 5) | 30); // fmov d30,x9; clears upper lane
        self.emit(0x6f00e41f); // movi v31.2d,#0
        self.emit(0x4e181c00 | (9 << 5) | 31); // ins v31.d[1],x9
    }

    pub(super) fn increment_native_counter(&mut self, field: usize) -> bool {
        if !self.native_counters_enabled() { return false; }
        let source = match field {
            state::CALLS => 30,
            state::RETURNS => 31,
            _ => return false,
        };
        // Independent wrapping u64 lanes; no carry crosses between counters.
        self.emit(0x4ee08400 | (source << 16) | (29 << 5) | 29);
        true
    }

    pub(super) fn save_native_counters(&mut self) {
        if !self.native_counters_enabled() { return; }
        // Exactly sixteen initialized host-owned bytes, including when State
        // has only its required eight-byte alignment. No adjacent field write.
        self.emit(0x3d800000 | ((state::CALLS as u32 / 16) << 10) | (19 << 5) | 29);
    }
}

#[cfg(test)]
#[path = "native_counters_tests.rs"]
mod tests;
