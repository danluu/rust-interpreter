//! Bounded, per-invocation indices over an immutable validated program.
//! Index entries are original case positions, preserving duplicate priority.
use crate::{Op, Program};

pub(crate) const MIN_CASES: usize = 32;
const MAX_CASES: usize = 65_536;
const MAX_ENTRIES: usize = 256;
const MAX_BYTES: usize = 1024 * 1024;
type Cases = [(u128, usize)];
type Key = (usize, usize);

#[inline]
pub(crate) fn linear(cases: &Cases, value: u128, otherwise: usize) -> usize {
    cases.iter().find(|(key, _)| *key == value).map_or(otherwise, |(_, target)| *target)
}

enum Index {
    Linear,
    Dense { base: u128, slots: Vec<usize> },
    Sorted(Vec<usize>),
}
impl Index {
    fn bytes(&self) -> usize {
        match self { Self::Linear => 0, Self::Dense { slots, .. } | Self::Sorted(slots) =>
            slots.capacity() * std::mem::size_of::<usize>() }
    }
    fn build(cases: &Cases, budget: usize) -> Option<Self> {
        if !(MIN_CASES..=MAX_CASES).contains(&cases.len()) { return None; }
        let (minimum, maximum) = cases.iter().fold((u128::MAX, 0), |(lo, hi), &(value, _)|
            (lo.min(value), hi.max(value)));
        let dense = maximum.checked_sub(minimum)?.checked_add(1)
            .filter(|&span| span <= (cases.len() * 4).min(MAX_CASES) as u128);
        let length = dense.map_or(cases.len(), |span| span as usize);
        if length.checked_mul(std::mem::size_of::<usize>())? > budget { return None; }
        let mut slots = Vec::new(); slots.try_reserve_exact(length).ok()?;
        if slots.capacity().checked_mul(std::mem::size_of::<usize>())? > budget { return None; }
        if dense.is_some() {
            slots.resize(length, 0);
            for (i, &(key, _)) in cases.iter().enumerate() {
                let slot = &mut slots[(key - minimum) as usize];
                if *slot == 0 { *slot = i + 1; } // zero is a missing key
            }
            Some(Self::Dense { base: minimum, slots })
        } else {
            slots.extend(0..cases.len());
            // Sorting by original position on ties retains the first case.
            slots.sort_unstable_by_key(|&i| (cases[i].0, i));
            Some(Self::Sorted(slots))
        }
    }
    fn target(&self, cases: &Cases, value: u128, otherwise: usize) -> usize {
        match self {
            Self::Linear => linear(cases, value, otherwise),
            Self::Dense { base, slots } => {
                let slot = value.checked_sub(*base).filter(|&offset| offset < slots.len() as u128)
                    .map_or(0, |offset| slots[offset as usize]);
                if slot == 0 { otherwise } else { cases[slot - 1].1 }
            }
            Self::Sorted(slots) => {
                let position = slots.partition_point(|&i| cases[i].0 < value);
                slots.get(position).filter(|&&i| cases[i].0 == value)
                    .map_or(otherwise, |&i| cases[i].1)
            }
        }
    }
}
struct Entry { key: Key, index: Index }
pub(crate) struct Cache<'a> {
    program: &'a Program,
    entries: Vec<Entry>,
    table_bytes: usize,
}
impl<'a> Cache<'a> {
    pub(crate) fn new(program: &'a Program) -> Self {
        Self { program, entries: Vec::new(), table_bytes: 0 }
    }
    pub(crate) fn target(&mut self, function: usize, pc: usize, value: u128) -> usize {
        let Op::Switch { cases, otherwise, .. } = &self.program.functions[function].code[pc] else {
            unreachable!("switch cache only receives validated Switch PCs")
        };
        let key = (function, pc);
        let position = match self.entries.binary_search_by_key(&key, |entry| entry.key) {
            Ok(position) => return self.entries[position].index.target(cases, value, *otherwise),
            Err(position) => position,
        };
        if self.entries.len() == MAX_ENTRIES { return linear(cases, value, *otherwise); }
        if self.entries.is_empty() && self.entries.try_reserve_exact(MAX_ENTRIES).is_err() {
            return linear(cases, value, *otherwise);
        }
        let overhead = self.entries.capacity().saturating_mul(std::mem::size_of::<Entry>());
        if overhead > MAX_BYTES {
            self.entries = Vec::new();
            return linear(cases, value, *otherwise);
        }
        let budget = MAX_BYTES.saturating_sub(overhead).saturating_sub(self.table_bytes);
        let index = Index::build(cases, budget).unwrap_or(Index::Linear);
        self.table_bytes += index.bytes();
        let target = index.target(cases, value, *otherwise);
        self.entries.insert(position, Entry { key, index });
        target
    }
}

#[cfg(test)]
#[path = "switch_index_tests.rs"]
mod tests;
