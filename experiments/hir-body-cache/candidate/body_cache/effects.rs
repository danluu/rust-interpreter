//! Exact cold-boundary effects. Process-local pointer identities never persist.
use std::collections::BTreeMap;
use std::sync::Arc;
use rustc_ast::{NodeId, node_id::NodeMap};
use rustc_hir as hir;
use rustc_span::Span;
use crate::{LoweringContext, PerOwnerLoweringState, TryBlockScope};
use super::{Candidate, journal};

#[derive(PartialEq, Eq)]
enum Child { Owner(usize), NonOwner(hir::HirId) }

#[derive(PartialEq, Eq)]
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

impl Frame {
    pub fn enter(lctx: &LoweringContext<'_, '_>, candidate: &Candidate) -> Option<Self> {
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

    pub fn validate_exit(&self, lctx: &LoweringContext<'_, '_>, candidate: &Candidate,
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

pub(super) enum Raw {
    Ast(NodeId, u32), Synthetic(u32), Bind(NodeId, Option<u32>, u32),
}
pub(crate) struct Trace {
    events: Vec<Raw>,
    rejected: Option<&'static str>,
}
impl Trace {
    pub fn new() -> Self { Self { events: Vec::new(), rejected: None } }
    pub fn reject(&mut self, reason: &'static str) { self.rejected.get_or_insert(reason); }
    fn push(&mut self, event: Raw) {
        if self.events.len() >= journal::MAX_EVENTS { self.reject("event-budget"); }
        else if self.rejected.is_none() { self.events.push(event); }
    }
    pub fn ast(&mut self, id: NodeId, local: hir::ItemLocalId) { self.push(Raw::Ast(id, local.as_u32())); }
    pub fn synthetic(&mut self, local: hir::ItemLocalId) { self.push(Raw::Synthetic(local.as_u32())); }
    pub fn binding(&mut self, id: NodeId, old: Option<hir::ItemLocalId>, new: hir::ItemLocalId) {
        self.push(Raw::Bind(id, old.map(|id| id.as_u32()), new.as_u32()));
    }
    pub fn finish(self, candidate: &Candidate, start: u32, end: u32, root: hir::HirId)
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
