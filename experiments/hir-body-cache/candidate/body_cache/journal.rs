//! Fallible, mutation-free event validation. Tree closure is checked separately.
use std::collections::{BTreeMap, BTreeSet};
use serde::{Deserialize, Serialize};

pub(super) const MAX_EVENTS: usize = 32768;

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub(super) enum Allocation { Ast(u32), Synthetic }

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub(super) enum Event {
    Allocate { source: Allocation, relative: u32 },
    Bind { ast: u32, relative: u32 },
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub(super) struct Journal {
    pub events: Vec<Event>,
    pub end_delta: u32,
    pub root_relative: u32,
}

/// Current, freshly resolved input. AST ordinals index this slice. Raw NodeIds
/// and old-session HirIds never enter the serialized journal.
#[derive(Clone, Debug)]
pub(super) struct Node {
    pub body: bool,
    pub binding: bool,
    pub traits: bool,
}

pub(super) struct Entry<'a> {
    pub start: u32,
    pub nodes: &'a [Node],
    pub prefix_bindings: &'a BTreeMap<u32, u32>,
}

/// Opaque, checked event layout. No lowering context or arena was mutated.
/// It is deliberately not convertible into a HIR expression: the complete
/// body wire-tree/reference validator must additionally succeed. No materializer exists.
pub(super) struct Checked {
    journal: Journal,
    pub start: u32,
    pub prefix_bindings: BTreeMap<u32, u32>,
    pub ast_allocations: BTreeMap<u32, u32>,
    pub bindings: BTreeMap<u32, u32>,
    pub trait_allocations: BTreeSet<u32>,
    pub end: u32,
}

impl Checked {
    pub fn journal(&self) -> &Journal { &self.journal }
}

pub(super) fn check(journal: Journal, entry: &Entry<'_>) -> Option<Checked> {
    let invalid = rustc_hir::ItemLocalId::INVALID.as_u32();
    if entry.start == 0 || entry.start >= invalid || entry.nodes.len() > 8192 || journal.events.len() > MAX_EVENTS
        || journal.end_delta == 0 || journal.root_relative >= journal.end_delta {
        return None;
    }
    let end = entry.start.checked_add(journal.end_delta)?;
    // INVALID is 0xFFFF_FF00 on this pinned compiler, not u32::MAX.
    // E is exclusive: it may equal INVALID, but every actual allocation must
    // be below it. Never construct a sentinel ID for a node or binding.
    if end > invalid { return None; }
    let mut prefix_ids = BTreeSet::new();
    for (&ordinal, &local) in entry.prefix_bindings {
        let node = entry.nodes.get(ordinal as usize)?;
        if node.body || !node.binding || local == 0 || local >= invalid || local >= entry.start
            || !prefix_ids.insert(local) { return None; }
    }
    for (ordinal, node) in entry.nodes.iter().enumerate() {
        if !node.body && node.binding && !entry.prefix_bindings.contains_key(&(ordinal as u32)) {
            return None;
        }
    }
    let mut ast_allocations = BTreeMap::new();
    let mut bindings = BTreeMap::new();
    let mut trait_allocations = BTreeSet::new();
    let mut next = 0_u32;
    for event in &journal.events {
        match *event {
            Event::Allocate { ref source, relative } => {
                if relative != next || relative >= journal.end_delta { return None; }
                next = next.checked_add(1)?;
                if let Allocation::Ast(ordinal) = *source {
                    let node = entry.nodes.get(ordinal as usize)?;
                    if !node.body || ast_allocations.insert(ordinal, relative).is_some() {
                        return None;
                    }
                    if node.traits { trait_allocations.insert(relative); }
                }
            }
            Event::Bind { ast, relative } => {
                let node = entry.nodes.get(ast as usize)?;
                if !node.body || !node.binding || ast_allocations.get(&ast) != Some(&relative)
                    || relative >= next || bindings.insert(ast, relative).is_some() {
                    return None;
                }
            }
        }
    }
    if next != journal.end_delta { return None; }
    for (&ordinal, &relative) in &ast_allocations {
        if entry.nodes[ordinal as usize].binding && bindings.get(&ordinal) != Some(&relative) {
            return None;
        }
    }
    Some(Checked { journal, start: entry.start, prefix_bindings: entry.prefix_bindings.clone(),
        ast_allocations, bindings, trait_allocations, end })
}

#[cfg(test)]
mod tests {
    use super::*;

    fn nodes() -> Vec<Node> {
        vec![Node { body: false, binding: true, traits: false },
             Node { body: true, binding: false, traits: true },
             Node { body: true, binding: true, traits: false }]
    }
    fn journal() -> Journal {
        Journal { events: vec![
            Event::Allocate { source: Allocation::Ast(1), relative: 0 },
            Event::Allocate { source: Allocation::Ast(2), relative: 1 },
            Event::Bind { ast: 2, relative: 1 },
            Event::Allocate { source: Allocation::Synthetic, relative: 2 },
        ], end_delta: 3, root_relative: 2 }
    }
    #[test]
    fn validates_s_relative_relocation_and_trait_presence() {
        let n = nodes();
        for start in [3, 41, 4096] {
            let prefix = BTreeMap::from([(0, start - 1)]);
            let checked = check(journal(), &Entry { start, nodes: &n, prefix_bindings: &prefix }).unwrap();
            assert_eq!(checked.end, start + 3);
            assert_eq!(checked.trait_allocations, BTreeSet::from([0]));
            assert_eq!(checked.bindings, BTreeMap::from([(2, 1)]));
        }
    }
    #[test]
    fn rejects_forward_bind_duplicate_ast_and_counter_gaps() {
        let n = nodes(); let prefix = BTreeMap::from([(0, 1)]);
        let entry = Entry { start: 3, nodes: &n, prefix_bindings: &prefix };
        let mut bad = journal(); bad.events.swap(1, 2); assert!(check(bad, &entry).is_none());
        let mut bad = journal(); bad.events[1] = Event::Allocate { source: Allocation::Ast(1), relative: 1 };
        assert!(check(bad, &entry).is_none());
        let mut bad = journal(); bad.events[0] = Event::Allocate { source: Allocation::Ast(1), relative: 1 };
        assert!(check(bad, &entry).is_none());
        let mut bad = journal(); bad.events.remove(2); assert!(check(bad, &entry).is_none());
    }
    #[test]
    fn rejects_prefix_aliases_body_prefixes_and_overflow() {
        let n = nodes();
        for prefix in [BTreeMap::new(), BTreeMap::from([(0, 3)]), BTreeMap::from([(2, 1)])] {
            assert!(check(journal(), &Entry { start: 3, nodes: &n, prefix_bindings: &prefix }).is_none());
        }
        let prefix = BTreeMap::from([(0, 1)]);
        assert!(check(journal(), &Entry { start: u32::MAX - 2, nodes: &n, prefix_bindings: &prefix }).is_none());
    }
    #[test]
    fn honors_actual_item_local_id_sentinel_and_exclusive_end() {
        let invalid = rustc_hir::ItemLocalId::INVALID.as_u32();
        assert_eq!(invalid, 0xFFFF_FF00);
        let n = nodes(); let prefix = BTreeMap::from([(0, 1)]);
        let one = Journal { events: vec![Event::Allocate {
            source: Allocation::Synthetic, relative: 0 }], end_delta: 1, root_relative: 0 };
        for start in [invalid - 2, invalid - 1] {
            let checked = check(one.clone(), &Entry { start, nodes: &n, prefix_bindings: &prefix }).unwrap();
            assert_eq!(checked.end, start + 1);
        }
        for start in [invalid, invalid + 1, u32::MAX] {
            assert!(check(one.clone(), &Entry { start, nodes: &n, prefix_bindings: &prefix }).is_none());
        }
        assert!(check(journal(), &Entry { start: invalid - 2, nodes: &n, prefix_bindings: &prefix }).is_none());
        for local in [invalid, invalid + 1] {
            let bad_prefix = BTreeMap::from([(0, local)]);
            assert!(check(one.clone(), &Entry { start: invalid - 1, nodes: &n, prefix_bindings: &bad_prefix }).is_none());
        }
    }
}
