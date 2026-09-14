//! Exact arbitrary-register liveness with sparse words and implicit fallthrough.
use super::*;

enum Words {
    Dense(Vec<u64>),
    Sparse { indices: Vec<u32>, bits: Vec<u64> },
}

struct ExceptionalSuccessors { pc: u32, start: u32, end: u32 }

pub(super) struct Compact {
    words: Words,
    stride: usize,
    pcs: usize,
    exceptions: Vec<ExceptionalSuccessors>,
    targets: Vec<u32>,
}

impl Compact {
    pub(super) fn new(live: &Liveness) -> Self {
        let nonzero = live.bits.iter().filter(|&&word| word != 0).count();
        let words = if nonzero * 12 < live.bits.len() * 8 {
            let mut indices = Vec::with_capacity(nonzero);
            let mut bits = Vec::with_capacity(nonzero);
            for (index, &word) in live.bits.iter().enumerate() {
                if word != 0 { indices.push(index as u32); bits.push(word); }
            }
            Words::Sparse { indices, bits }
        } else { Words::Dense(live.bits.clone()) };
        let special = |pc: usize, next: &[usize]| next != [pc + 1];
        let count = live.successors.iter().enumerate().filter(|(pc, next)| special(*pc, next)).count();
        let target_count: usize = live.successors.iter().enumerate()
            .filter(|(pc, next)| special(*pc, next)).map(|(_, next)| next.len()).sum();
        let mut exceptions = Vec::with_capacity(count);
        let mut targets = Vec::with_capacity(target_count);
        for (pc, next) in live.successors.iter().enumerate() {
            if !special(pc, next) { continue; }
            let start = targets.len();
            targets.extend(next.iter().map(|&target| target as u32));
            exceptions.push(ExceptionalSuccessors { pc: pc as u32, start: start as u32, end: targets.len() as u32 });
        }
        // ranked() already bounds PCs/word indices/edges well below u32::MAX.
        Self { words, stride: live.stride, pcs: live.successors.len(), exceptions, targets }
    }

    pub(super) fn at(&self, pc: usize, reg: Reg) -> bool {
        if pc >= self.pcs || reg as usize / 64 >= self.stride { return false; }
        let index = pc * self.stride + reg as usize / 64;
        let word = match &self.words {
            Words::Dense(bits) => bits.get(index),
            Words::Sparse { indices, bits } => indices.binary_search(&(index as u32)).ok().map(|i| &bits[i]),
        };
        word.is_some_and(|word| word & (1 << (reg % 64)) != 0)
    }

    pub(super) fn after(&self, pc: usize, reg: Reg) -> bool {
        if pc >= self.pcs { return false; }
        match self.exceptions.binary_search_by_key(&(pc as u32), |row| row.pc) {
            Ok(index) => {
                let row = &self.exceptions[index];
                self.targets[row.start as usize..row.end as usize].iter().any(|&target| self.at(target as usize, reg))
            }
            Err(_) => self.at(pc + 1, reg),
        }
    }

    pub(super) fn capacities(&self) -> [usize; 4] {
        let (bits, indices) = match &self.words {
            Words::Dense(bits) => (bits.capacity() * 8, 0),
            Words::Sparse { indices, bits } => (bits.capacity() * 8, indices.capacity() * 4),
        };
        [bits, indices, self.exceptions.capacity() * std::mem::size_of::<ExceptionalSuccessors>(), self.targets.capacity() * 4]
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn dense_and_sparse_words_preserve_all_register_queries_and_successors() {
        for registers in [8, 4096] {
            let f = Function { name: "compact query".into(), frame_size: 16, frame_align: 16,
                args: vec![], result: crate::Slot { offset: 0, size: 0 }, registers,
                code: vec![Op::Load { dst: 1, address: 0, size: 8 },
                    Op::Switch { value: 1, cases: vec![(0, 0), (1, 3)], otherwise: 2 },
                    Op::Store { address: 0, src: 1, size: 8 }, Op::Return] };
            let allocation = analyze(&f).unwrap();
            assert_eq!(matches!(allocation.compact.words, Words::Sparse { .. }), registers == 4096);
            for pc in 0..=f.code.len() { for reg in 0..registers as Reg {
                assert_eq!(allocation.live_at(pc, reg), allocation.live.at(pc, reg));
                assert_eq!(allocation.live_after(pc, reg), allocation.live.after(pc, reg));
            } }
            assert!(!allocation.live_at(usize::MAX, u32::MAX));
            assert!(!allocation.live_after(usize::MAX, u32::MAX));
        }
    }
}
