//! Exact cold-boundary effects. Process-local pointer identities never persist.
use std::collections::BTreeMap;
use std::sync::Arc;
use rustc_ast::{NodeId, node_id::NodeMap};
use rustc_hir as hir;
use rustc_span::Span;
use crate::{LoweringContext, PerOwnerLoweringState, TryBlockScope};
use super::{Candidate, journal};

#[derive(Clone, PartialEq, Eq)]
enum Child { Owner(usize), NonOwner(hir::HirId) }

#[derive(Clone, PartialEq, Eq)]
struct Unchanged {
    resolver: usize,
    arena: usize,
    owner: usize,
    owner_id: hir::OwnerId,
    disambiguator: hir::definitions::PerParentDisambiguatorState,
    next_node: NodeId,
    current_item: Option<Span>,
    attrs: Vec<(u32, usize, usize)>,
    bodies: Vec<(u32, usize)>,
    children: BTreeMap<u32, Child>,
    opaque: Option<(usize, usize)>,
    allowed_features: Vec<usize>,
}

/// Exhaustive destructuring is intentional: adding a compiler field requires
/// an explicit decision here. Mutable internals without safe comparison are
/// rejected or guarded at their exact mutation entry point in the patch.
fn unchanged(lctx: &LoweringContext<'_, '_>) -> Option<Unchanged> {
    let LoweringContext { tcx: _, resolver, curr_owner, arena,
        contract_ensures, coroutine_kind, task_context, current_item,
        try_block_scope, loop_scope, is_in_loop_condition, is_in_dyn_type,
        next_node_id, node_id_to_def_id, partial_res_overrides,
        allow_contracts, allow_try_trait, allow_gen_future, allow_pattern_type,
        allow_async_gen, allow_async_iterator, allow_for_await, allow_async_fn_traits,
        move_expr_bindings, attribute_parser: _, body_candidate: _, body_trace: _ } = lctx;
    let PerOwnerLoweringState { owner, owner_id, disambiguator, item_local_id_counter: _,
        ident_and_label_to_local_id: _,
        #[cfg(debug_assertions)] relowering_checker: _,
        attrs, bodies, define_opaque, trait_map: _, delayed_lints, children,
        impl_trait_defs, impl_trait_bounds } = curr_owner;
    if contract_ensures.is_some() || coroutine_kind.is_some() || task_context.is_some()
        || !matches!(try_block_scope, TryBlockScope::Function) || loop_scope.is_some()
        || *is_in_loop_condition || *is_in_dyn_type || !move_expr_bindings.is_empty()
        || !node_id_to_def_id.is_empty() || !partial_res_overrides.is_empty()
        || !delayed_lints.is_empty() || !impl_trait_defs.is_empty() || !impl_trait_bounds.is_empty() {
        return None;
    }
    // Nonempty preexisting attrs/children/bodies are preserved byte-for-byte by
    // immutable object identity, rather than incorrectly requiring whole-owner
    // emptiness. Empty delayed_lints avoids comparing/replaying FnOnce callbacks.
    let children = children.items().map(|(id, value)| {
        let value = match value {
            hir::MaybeOwner::Owner(info) => Child::Owner(*info as *const _ as usize),
            hir::MaybeOwner::NonOwner(id) => Child::NonOwner(*id),
        };
        (id.local_def_index.as_u32(), value)
    }).into_sorted_stable_ord_by_key(|x| &x.0).into_iter().collect();
    let allowed_features = [allow_contracts, allow_try_trait, allow_gen_future, allow_pattern_type,
        allow_async_gen, allow_async_iterator, allow_for_await, allow_async_fn_traits]
        .into_iter().map(|value| Arc::as_ptr(value) as *const () as usize).collect();
    Some(Unchanged { resolver: *resolver as *const _ as usize, arena: *arena as *const _ as usize,
        owner: *owner as *const _ as usize, owner_id: *owner_id, disambiguator: disambiguator.clone(), next_node: *next_node_id,
        current_item: *current_item,
        attrs: attrs.iter().map(|(id, value)| (id.as_u32(), value.as_ptr() as usize, value.len())).collect(),
        bodies: bodies.iter().map(|(id, value)| (id.as_u32(), *value as *const _ as usize)).collect(),
        children, opaque: define_opaque.map(|value| (value.as_ptr() as usize, value.len())), allowed_features })
}

fn traits(lctx: &LoweringContext<'_, '_>) -> BTreeMap<u32, (usize, usize)> {
    lctx.curr_owner.trait_map.items().map(|(id, value)|
        (id.as_u32(), (value.as_ptr() as usize, value.len())))
        .into_sorted_stable_ord_by_key(|x| &x.0).into_iter().collect()
}

pub(super) struct Frame {
    unchanged: Unchanged,
    pub start: u32,
    bindings: NodeMap<hir::ItemLocalId>,
    traits: BTreeMap<u32, (usize, usize)>,
    #[cfg(debug_assertions)] debug_nodes: NodeMap<hir::ItemLocalId>,
    pub prefix: BTreeMap<u32, u32>,
}

/// Actual current IDs and immutable current trait slices, never deserialized.
pub(super) enum ReplayEvent {
    Ast { node: NodeId, id: hir::HirId },
    Synthetic(hir::HirId),
    Bind { node: NodeId, local: hir::ItemLocalId },
}
pub(super) struct ReplayExit<'hir> {
    unchanged: Unchanged,
    end: u32,
    bindings: NodeMap<hir::ItemLocalId>,
    traits: BTreeMap<u32, &'hir [hir::TraitCandidate<'hir>]>,
    #[cfg(debug_assertions)] debug_nodes: NodeMap<hir::ItemLocalId>,
}
fn trait_values<'hir>(lctx: &LoweringContext<'_, 'hir>) -> BTreeMap<u32, &'hir [hir::TraitCandidate<'hir>]> {
    lctx.curr_owner.trait_map.items().map(|(id, value)| (id.as_u32(), *value))
        .into_sorted_stable_ord_by_key(|x| &x.0).into_iter().collect()
}
fn same_traits(a: &[hir::TraitCandidate<'_>], b: &[hir::TraitCandidate<'_>]) -> bool {
    a.len() == b.len() && a.iter().zip(b).all(|(a, b)| {
        let hir::TraitCandidate { def_id: a_def, import_ids: a_imports, lint_ambiguous: a_lint } = a;
        let hir::TraitCandidate { def_id: b_def, import_ids: b_imports, lint_ambiguous: b_lint } = b;
        a_def == b_def && a_imports == b_imports && a_lint == b_lint
    })
}
fn vacant_range(start: u32, end: u32, occupied: impl IntoIterator<Item = u32>) -> bool {
    start > 0 && start < end && end <= hir::ItemLocalId::INVALID.as_u32()
        && !occupied.into_iter().any(|id| start <= id && id < end)
}
fn reserve_node(map: &mut NodeMap<hir::ItemLocalId>, node: NodeId, local: hir::ItemLocalId) -> Option<()> {
    if map.contains_key(&node) { return None; }
    map.insert(node, local);
    Some(())
}
impl ReplayExit<'_> {
    pub(super) fn assert_matches(&self, lctx: &LoweringContext<'_, '_>) {
        assert!(lctx.body_trace.is_none(), "HIR body replay retained its trace");
        assert!(lctx.body_candidate.is_none(), "HIR body replay introduced a candidate");
        assert!(lctx.tcx.dcx().has_errors().is_none(), "HIR body replay emitted diagnostics");
        assert!(unchanged(lctx).is_some_and(|value| value == self.unchanged), "HIR body replay changed an excluded effect");
        assert_eq!(lctx.curr_owner.item_local_id_counter.as_u32(), self.end);
        assert!(lctx.curr_owner.ident_and_label_to_local_id == self.bindings, "HIR body replay binding mismatch");
        let actual = trait_values(lctx);
        assert!(actual.len() == self.traits.len() && actual.iter().all(|(id, actual)|
            self.traits.get(id).is_some_and(|expected| same_traits(actual, expected))), "HIR body replay trait mismatch");
        #[cfg(debug_assertions)]
        assert!(lctx.curr_owner.relowering_checker.body_snapshot().is_some_and(|actual| actual == self.debug_nodes));
    }
}

impl Frame {
    fn same_entry(&self, lctx: &LoweringContext<'_, '_>) -> bool {
        lctx.body_trace.is_none() && lctx.body_candidate.is_none() && lctx.tcx.dcx().has_errors().is_none()
            && unchanged(lctx).is_some_and(|value| value == self.unchanged)
            && lctx.curr_owner.item_local_id_counter.as_u32() == self.start
            && lctx.curr_owner.ident_and_label_to_local_id == self.bindings && traits(lctx) == self.traits
            && {
                #[cfg(debug_assertions)]
                { lctx.curr_owner.relowering_checker.body_snapshot().is_some_and(|value| value == self.debug_nodes) }
                #[cfg(not(debug_assertions))]
                { true }
            }
    }
    pub(super) fn assert_unchanged_miss(&self, lctx: &LoweringContext<'_, '_>) {
        assert!(self.same_entry(lctx), "HIR body miss mutated its entry context");
    }
    pub(super) fn replay_plan<'hir>(&self, lctx: &LoweringContext<'_, 'hir>, candidate: &Candidate,
        checked: &journal::Checked) -> Option<(Vec<ReplayEvent>, ReplayExit<'hir>)> {
        if !self.same_entry(lctx) || candidate.owner != lctx.curr_owner.owner_id
            || checked.start != self.start || checked.prefix_bindings != self.prefix { return None; }
        let reserved = |id: u32| self.start <= id && id < checked.end;
        // All body attribute/alias source slots are empty. No preexisting body,
        // trait or debug entry may be overwritten by a recorded destination.
        if !vacant_range(self.start, checked.end,
            lctx.curr_owner.attrs.iter().map(|(id, _)| id.as_u32())
                .chain(lctx.curr_owner.bodies.iter().map(|(id, _)| id.as_u32()))
                .chain(self.traits.keys().copied())) { return None; }
        for &(node, body) in &candidate.ast_nodes {
            if body && lctx.opt_local_def_id(node).is_some() { return None; }
        }
        let mut bindings = self.bindings.clone(); let mut traits = trait_values(lctx);
        #[cfg(debug_assertions)] let mut debug_nodes = self.debug_nodes.clone();
        let mut plan = Vec::with_capacity(checked.journal().events.len());
        for event in &checked.journal().events {
            match *event {
                journal::Event::Allocate { ref source, relative } => {
                    let local = self.start.checked_add(relative)?;
                    if !reserved(local) || local >= hir::ItemLocalId::INVALID.as_u32() { return None; }
                    let id = hir::HirId { owner: candidate.owner, local_id: hir::ItemLocalId::from_u32(local) };
                    match *source {
                        journal::Allocation::Synthetic => plan.push(ReplayEvent::Synthetic(id)),
                        journal::Allocation::Ast(ordinal) => {
                            let (node, body) = *candidate.ast_nodes.get(ordinal as usize)?;
                            if !body || node == rustc_ast::DUMMY_NODE_ID || lctx.opt_local_def_id(node).is_some() { return None; }
                            #[cfg(debug_assertions)]
                            reserve_node(&mut debug_nodes, node, id.local_id)?;
                            let slice = lctx.curr_owner.owner.trait_map.get(&node).copied();
                            if slice.is_some() != checked.trait_allocations.contains(&relative) { return None; }
                            if let Some(slice) = slice {
                                if traits.insert(local, slice).is_some() { return None; }
                            }
                            plan.push(ReplayEvent::Ast { node, id });
                        }
                    }
                }
                journal::Event::Bind { ast, relative } => {
                    let (node, body) = *candidate.ast_nodes.get(ast as usize)?;
                    if !body || checked.bindings.get(&ast) != Some(&relative) { return None; }
                    let local = self.start.checked_add(relative)?;
                    if !reserved(local) || local >= hir::ItemLocalId::INVALID.as_u32() { return None; }
                    let local = hir::ItemLocalId::from_u32(local);
                    reserve_node(&mut bindings, node, local)?;
                    plan.push(ReplayEvent::Bind { node, local });
                }
            }
        }
        Some((plan, ReplayExit { unchanged: self.unchanged.clone(), end: checked.end,
            bindings, traits, #[cfg(debug_assertions)] debug_nodes }))
    }
    pub(super) fn enter(lctx: &LoweringContext<'_, '_>, candidate: &Candidate) -> Option<Self> {
        if lctx.body_trace.is_some() || lctx.tcx.dcx().has_errors().is_some() { return None; }
        let start = lctx.curr_owner.item_local_id_counter.as_u32();
        let mut prefix = BTreeMap::new();
        let bindings = lctx.curr_owner.ident_and_label_to_local_id.clone();
        // Every current binding must belong to the normally lowered parameter
        // prefix. Hidden caller/closure bindings are an unsupported context.
        for (_, (id, local)) in bindings.items().map(|(id, local)| (id.as_u32(), (id, local)))
            .into_sorted_stable_ord_by_key(|x| &x.0) {
            let ordinal = *candidate.ordinals.get(id)?;
            let node = candidate.nodes.get(ordinal as usize)?;
            if node.body || !node.binding || local.as_u32() == 0 || local.as_u32() >= start { return None; }
            prefix.insert(ordinal, local.as_u32());
        }
        Some(Self { unchanged: unchanged(lctx)?, start, bindings, traits: traits(lctx), prefix,
            #[cfg(debug_assertions)] debug_nodes: lctx.curr_owner.relowering_checker.body_snapshot()? })
    }

    pub(super) fn validate_exit(&self, lctx: &LoweringContext<'_, '_>, candidate: &Candidate,
        checked: &journal::Checked) -> Option<()> {
        if lctx.tcx.dcx().has_errors().is_some() || unchanged(lctx)? != self.unchanged
            || lctx.curr_owner.item_local_id_counter.as_u32() != checked.end { return None; }
        let mut bindings = self.bindings.clone();
        for (&ordinal, &relative) in &checked.bindings {
            let id = candidate.ast_nodes.get(ordinal as usize)?.0;
            if bindings.insert(id, hir::ItemLocalId::from_u32(self.start.checked_add(relative)?)).is_some() {
                return None;
            }
        }
        if bindings != lctx.curr_owner.ident_and_label_to_local_id { return None; }
        let mut expected_traits = self.traits.clone();
        for (&ordinal, &relative) in &checked.ast_allocations {
            let ast = candidate.ast_nodes.get(ordinal as usize)?.0;
            if let Some(value) = lctx.curr_owner.owner.trait_map.get(&ast) {
                if !checked.trait_allocations.contains(&relative) { return None; }
                let local = self.start.checked_add(relative)?;
                if expected_traits.insert(local, (value.as_ptr() as usize, value.len())).is_some() { return None; }
            } else if checked.trait_allocations.contains(&relative) { return None; }
        }
        if expected_traits != traits(lctx) { return None; }
        #[cfg(debug_assertions)] {
            let mut expected = self.debug_nodes.clone();
            for (&ordinal, &relative) in &checked.ast_allocations {
                let ast = candidate.ast_nodes.get(ordinal as usize)?.0;
                if expected.insert(ast, hir::ItemLocalId::from_u32(self.start.checked_add(relative)?)).is_some() {
                    return None;
                }
            }
            if expected != lctx.curr_owner.relowering_checker.body_snapshot()? { return None; }
        }
        Some(())
    }
}

#[cfg(test)]
mod replay_tests {
    use super::*;
    #[test]
    fn preflight_rejects_occupied_body_slots_and_preserves_exclusive_end() {
        assert!(vacant_range(3, 6, [1, 2, 6, 20]));
        for occupied in [3, 4, 5] { assert!(!vacant_range(3, 6, [1, occupied, 6])); }
        let invalid = hir::ItemLocalId::INVALID.as_u32();
        assert!(vacant_range(invalid - 1, invalid, [1, invalid - 2]));
        for (start, end) in [(0, 3), (3, 3), (6, 3), (invalid, invalid + 1), (invalid - 1, invalid + 1)] {
            assert!(!vacant_range(start, end, []));
        }
    }
    #[test]
    fn preflight_binding_and_debug_reservations_never_overwrite() {
        let node = NodeId::from_u32(7); let other = NodeId::from_u32(8);
        let old = hir::ItemLocalId::from_u32(2); let new = hir::ItemLocalId::from_u32(3);
        let mut map = NodeMap::default(); map.insert(node, old);
        let original = map.clone();
        assert!(reserve_node(&mut map, node, new).is_none());
        assert_eq!(map, original);
        assert!(reserve_node(&mut map, other, new).is_some());
        assert_eq!(map.get(&node), Some(&old)); assert_eq!(map.get(&other), Some(&new));
        let expected = map.clone();
        assert!(reserve_node(&mut map, other, new).is_none()); assert_eq!(map, expected);
    }
    #[test]
    fn replay_trait_equality_retains_imports_lints_order_and_duplicates() {
        let id = rustc_span::def_id::CRATE_DEF_ID;
        fn candidate(imports: &[rustc_span::def_id::LocalDefId], lint: bool) -> hir::TraitCandidate<'_> {
            hir::TraitCandidate { def_id: rustc_span::def_id::CRATE_DEF_ID.to_def_id(),
                import_ids: imports, lint_ambiguous: lint }
        }
        let imports = [id];
        assert!(same_traits(&[candidate(&imports, false)], &[candidate(&imports, false)]));
        let mut other_definition = candidate(&imports, false);
        other_definition.def_id.index = rustc_span::def_id::DefIndex::from_u32(1);
        assert!(!same_traits(&[candidate(&imports, false)], &[other_definition]));
        assert!(!same_traits(&[candidate(&imports, false)], &[candidate(&[], false)]));
        assert!(!same_traits(&[candidate(&imports, false)], &[candidate(&imports, true)]));
        assert!(!same_traits(&[candidate(&[], false), candidate(&[], true)],
            &[candidate(&[], true), candidate(&[], false)]));
        assert!(!same_traits(&[candidate(&[], false)], &[candidate(&[], false), candidate(&[], false)]));
    }
}

pub(super) enum Raw {
    Ast(NodeId, u32), Synthetic(u32), Bind(NodeId, Option<u32>, u32),
}
pub(crate) struct Trace {
    events: Vec<Raw>,
    rejected: Option<&'static str>,
}
impl Trace {
    pub(super) fn new() -> Self { Self { events: Vec::new(), rejected: None } }
    pub(crate) fn reject(&mut self, reason: &'static str) { self.rejected.get_or_insert(reason); }
    fn push(&mut self, event: Raw) {
        if self.events.len() >= journal::MAX_EVENTS { self.reject("event-budget"); }
        else if self.rejected.is_none() { self.events.push(event); }
    }
    pub(crate) fn ast(&mut self, id: NodeId, local: hir::ItemLocalId) { self.push(Raw::Ast(id, local.as_u32())); }
    pub(crate) fn synthetic(&mut self, local: hir::ItemLocalId) { self.push(Raw::Synthetic(local.as_u32())); }
    pub(crate) fn binding(&mut self, id: NodeId, old: Option<hir::ItemLocalId>, new: hir::ItemLocalId) {
        self.push(Raw::Bind(id, old.map(|id| id.as_u32()), new.as_u32()));
    }
    pub(super) fn finish(self, candidate: &Candidate, start: u32, end: u32, root: hir::HirId)
        -> Option<journal::Journal> {
        if self.rejected.is_some() || root.owner != candidate.owner { return None; }
        let mut events = Vec::with_capacity(self.events.len());
        for event in self.events {
            events.push(match event {
                Raw::Ast(id, local) => journal::Event::Allocate {
                    source: journal::Allocation::Ast(*candidate.ordinals.get(&id)?), relative: local.checked_sub(start)? },
                Raw::Synthetic(local) => journal::Event::Allocate {
                    source: journal::Allocation::Synthetic, relative: local.checked_sub(start)? },
                Raw::Bind(id, None, local) => journal::Event::Bind {
                    ast: *candidate.ordinals.get(&id)?, relative: local.checked_sub(start)? },
                Raw::Bind(_, Some(_), _) => return None,
            });
        }
        Some(journal::Journal { events, end_delta: end.checked_sub(start)?,
            root_relative: root.local_id.as_u32().checked_sub(start)? })
    }
}
