//! Validate an existing whole-run profile against typed bytecode before weighting
//! the offline register census. No safety property is inferred from Debug text.
use crate::{Function, Program};
use serde::Deserialize;

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
pub(super) struct Profile { pub functions: Vec<FunctionProfile> }

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
pub(super) struct FunctionProfile {
    name: String,
    frame_size: usize,
    registers: usize,
    operations: Vec<String>,
    pub interpreted: Vec<u64>,
    pub jit_blocks: Vec<u64>,
    jit_block_ends: Vec<usize>,
    jit_tree_blocks: Vec<u64>,
    jit_tree_block_ends: Vec<usize>,
}

pub(super) fn parse(program: &Program, bytes: &[u8]) -> Result<Profile, String> {
    if bytes.len() > 256 * 1024 * 1024 { return Err("profile exceeds 256 MiB".into()); }
    let profile: Profile = serde_json::from_slice(bytes).map_err(|e| e.to_string())?;
    if profile.functions.len() != program.functions.len() { return Err("profile function count mismatch".into()); }
    for (f, p) in program.functions.iter().zip(&profile.functions) { p.native_counts(f)?; }
    Ok(profile)
}

impl FunctionProfile {
    pub(super) fn intervals(&self) -> impl Iterator<Item = (usize, usize, u64)> + '_ {
        self.jit_blocks.iter().zip(&self.jit_block_ends).enumerate()
            .filter_map(|(pc, (&hits, &end))| (hits != 0).then_some((pc, end, hits)))
    }

    pub(super) fn native_counts(&self, f: &Function) -> Result<Vec<u64>, String> {
        let n = f.code.len();
        if self.name != f.name || self.frame_size != f.frame_size || self.registers != f.registers
            || self.operations.len() != n
            || self.operations.iter().zip(&f.code).any(|(a, b)| a != &format!("{b:?}"))
        { return Err("profile bytecode shape mismatch".into()); }
        if self.interpreted.len() != n || self.jit_blocks.len() != n || self.jit_block_ends.len() != n
            || self.jit_tree_blocks.len() != n || self.jit_tree_block_ends.len() != n
        { return Err("profile counter shape mismatch".into()); }
        if self.jit_tree_blocks.iter().any(|&v| v != 0) || self.jit_tree_block_ends.iter().any(|&v| v != 0) {
            return Err("width census requires a profile without native trees".into());
        }
        // Difference events make reconstruction linear even with overlapping
        // compiled intervals. Checked accumulation rejects overflowing counts.
        let mut starts = vec![0u64; n + 1];
        let mut ends = vec![0u64; n + 1];
        for (pc, (&hits, &end)) in self.jit_blocks.iter().zip(&self.jit_block_ends).enumerate() {
            if end != 0 && !(pc < end && end <= n) { return Err("invalid native profile interval".into()); }
            if hits != 0 {
                if end == 0 { return Err("native profile hits without interval".into()); }
                starts[pc] = hits;
                ends[end] = ends[end].checked_add(hits).ok_or("profile count overflow")?;
            }
        }
        let mut active = 0u64;
        let mut counts = Vec::with_capacity(n);
        for pc in 0..n {
            active = active.checked_sub(ends[pc]).and_then(|v| v.checked_add(starts[pc]))
                .ok_or("profile count overflow")?;
            counts.push(active);
        }
        if active != ends[n] { return Err("unbalanced native profile intervals".into()); }
        Ok(counts)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{Op, Slot};
    fn inputs() -> (Function, FunctionProfile) {
        let f = Function { name:"counts".into(),frame_size:0,frame_align:16,registers:1,
            args:vec![],result:Slot{offset:0,size:0},
            code:vec![Op::Imm {dst:0,value:0},Op::Jump {target:0},Op::Return] };
        let p = FunctionProfile { name:f.name.clone(),frame_size:0,registers:1,
            operations:f.code.iter().map(|op|format!("{op:?}")).collect(),interpreted:vec![1,0,0],
            jit_blocks:vec![10,2,4],jit_block_ends:vec![2,3,3],
            jit_tree_blocks:vec![0;3],jit_tree_block_ends:vec![0;3] };
        (f,p)
    }
    #[test]
    fn profile_reconstructs_overlapping_intervals_and_zero_hit_blocks() {
        let (f,mut p)=inputs();
        assert_eq!(p.native_counts(&f).unwrap(),[10,12,6]);
        p.jit_blocks[1]=0;
        assert_eq!(p.native_counts(&f).unwrap(),[10,10,4]);
    }
    #[test]
    fn profile_rejects_mismatched_code_shapes_and_native_trees() {
        let (f,mut p)=inputs();p.operations[0]="Imm { dst: 0, value: 1 }".into();
        assert!(p.native_counts(&f).is_err());
        let (f,mut p)=inputs();p.name="other".into();assert!(p.native_counts(&f).is_err());
        let (f,mut p)=inputs();p.jit_blocks.pop();assert!(p.native_counts(&f).is_err());
        let (f,mut p)=inputs();p.jit_tree_blocks[0]=1;assert!(p.native_counts(&f).is_err());
    }
    #[test]
    fn profile_rejects_bad_intervals_and_counter_overflow() {
        for end in [0,1,4] {
            let (f,mut p)=inputs();p.jit_block_ends[1]=end;assert!(p.native_counts(&f).is_err());
        }
        let (f,mut p)=inputs();p.jit_blocks[0]=u64::MAX;assert!(p.native_counts(&f).is_err());
        let (f,mut p)=inputs();p.jit_blocks[1]=u64::MAX;assert!(p.native_counts(&f).is_err());
    }
}
