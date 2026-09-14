//! Relocate cached native continuations before publishing a staged function.
use super::*;

impl CompiledFunction<'_> {
    pub(super) fn relocate_continuations(&mut self, base: usize) -> Result<(), EmitError> {
        let invalid = || EmitError::InvalidRelocation("invalid cached continuation relocation");
        let end = self.words.len().checked_mul(4).and_then(|n| base.checked_add(n)).ok_or_else(invalid)?;
        if base % 4 != 0 || end > MAX_CODE_BYTES { return Err(invalid()); }
        let offset = |pc: usize| -> Result<u32, EmitError> {
            let target = self.resumes.get(pc).ok_or_else(invalid)?;
            let Some(word) = *target else { return Ok(0); };
            let value = word.checked_mul(4).and_then(|n| base.checked_add(n)).ok_or_else(invalid)?;
            // An actual resume follows the saved-host prologue and therefore
            // cannot be arena offset zero. Missing targets alone encode zero.
            if word >= self.words.len() || value == 0 || value >= end { return Err(invalid()); }
            u32::try_from(value).map_err(|_| invalid())
        };
        // Validate every slot and target before modifying any staged words.
        // Metadata is emitted in increasing order and cannot alias a slot.
        let mut previous_end = 0;
        for &(at, pc) in &self.continuations {
            if at < previous_end || at.checked_add(2).is_none_or(|end| end > self.words.len())
                || self.words[at] != 0x5280000a || self.words[at + 1] != 0x72a0000a {
                return Err(invalid());
            }
            previous_end = at + 2;
            offset(pc)?;
        }
        let values: Vec<_> = self.continuations.iter().map(|&(_, pc)| offset(pc)).collect::<Result<_, _>>()?;
        for (&(at, _), value) in self.continuations.iter().zip(values) {
            self.words[at] |= (value & 0xffff) << 5;
            self.words[at + 1] |= (value >> 16) << 5;
        }
        Ok(())
    }
}

#[cfg(all(test, target_arch = "aarch64", target_os = "macos"))]
mod tests;
