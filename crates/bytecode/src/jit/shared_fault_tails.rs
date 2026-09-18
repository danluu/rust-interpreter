//! Share complete identical terminal fault returns within one staged function.
use super::{BTreeMap, CodegenLimit, EmitError, branch_displacement};

const MAX_KEYS: usize = 256;
const MAX_WORDS: usize = 32;

#[derive(Default)]
pub(super) struct Tails {
    retained: BTreeMap<Vec<u32>, usize>,
}

impl Tails {
    /// The sole production caller supplies status materialization followed by
    /// return_to_vm: a position-independent, straight-line terminal sequence.
    /// The retained copy is never truncated or patched. Targets and sources
    /// use function-relative word offsets, so no published address is cached.
    /// A local branch replaces the complete duplicate; conditional fault edges
    /// keep their original local label and conditional-branch range contract.
    pub(super) fn share(&mut self, words: &mut Vec<u32>, start: usize, base: usize)
        -> Result<(), EmitError>
    {
        let tail = words.get(start..).ok_or(EmitError::InvalidRelocation("invalid fault tail start"))?;
        if !(2..=MAX_WORDS).contains(&tail.len()) || tail.last() != Some(&0xd65f03c0) {
            return Ok(());
        }
        let source = base.checked_add(start).ok_or(EmitError::InvalidRelocation("fault tail offset overflow"))?;
        if let Some(&target) = self.retained.get(tail) {
            // If future capacities exceed B's reach, retain the original tail.
            if let Ok(displacement) = branch_displacement(source, target, 26, CodegenLimit::Jump) {
                words.truncate(start);
                words.push(0x14000000 | displacement);
            }
        } else if self.retained.len() < MAX_KEYS {
            self.retained.insert(tail.to_vec(), source);
        }
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn tail(status: u32) -> Vec<u32> { vec![0xd2800000 | (status << 5), 0xd65f03c0] }

    #[test]
    fn identical_terminal_tails_share_only_inside_their_function() {
        let mut table=Tails::default();
        let original=tail(7);
        let mut first=original.clone();
        table.share(&mut first,0,100).unwrap();
        assert_eq!(first,original);
        let mut second=vec![0xd503201f];
        second.extend(&original);
        table.share(&mut second,1,200).unwrap();
        assert_eq!(second,[0xd503201f,0x14000000 | ((-101i32 as u32)&0x3ffffff)]);
        let mut different=tail(8);
        table.share(&mut different,0,300).unwrap();
        assert_eq!(different,tail(8));
        let mut new_function=original.clone();
        Tails::default().share(&mut new_function,0,0).unwrap();
        assert_eq!(new_function,original);
    }

    #[test]
    fn bounded_or_unreachable_tail_keys_keep_original_words() {
        let mut table=Tails::default();
        for status in 0..MAX_KEYS as u32 {
            table.share(&mut tail(status),0,status as usize*8).unwrap();
        }
        assert_eq!(table.retained.len(),MAX_KEYS);
        for _ in 0..2 {
            let mut fresh=tail(1000);
            table.share(&mut fresh,0,8192).unwrap();
            assert_eq!(fresh,tail(1000));
        }
        let mut distant=tail(0);
        table.share(&mut distant,0,1<<26).unwrap();
        assert_eq!(distant,tail(0));
        let mut large=vec![0xd503201f;MAX_WORDS];
        large.push(0xd65f03c0);
        let saved=large.clone();
        table.share(&mut large,0,16384).unwrap();
        assert_eq!(large,saved);
        assert!(table.share(&mut vec![],1,0).is_err());
    }
}

#[cfg(all(test,target_arch="aarch64",target_os="macos"))]
#[path="shared_fault_tails_tests.rs"]
mod native_tests;
