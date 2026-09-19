//! The only real commit adapter. No public token constructor or HIR shortcut.
//! Every None is produced before constructing ReadyHit or changing the context.
use super::*;
use super::super::{Candidate, capture, effects::{Frame, ReplayEvent, ReplayExit, Trace}, entry, journal, storage};

struct ReadyHit<'context, 'candidate, 'ast, 'hir> {
    context: &'context mut crate::LoweringContext<'ast, 'hir>,
    candidate: &'candidate Candidate,
    checked: journal::Checked,
    body: BodyValues,
    events: Vec<ReplayEvent>,
    expected_exit: ReplayExit<'hir>,
}
impl<'hir> ReadyHit<'_, '_, '_, 'hir> {
    /// No failure return and no cold retry after the first recorded effect.
    /// OOM/internal invariant failure remains ordinary compiler failure.
    fn commit(self) -> hir::Expr<'hir> {
        let Self { context, candidate, checked, body, events, expected_exit } = self;
        assert_eq!(context.curr_owner.owner_id, body.owner);
        assert_eq!(context.curr_owner.item_local_id_counter.as_u32(), body.start);
        assert!(context.body_trace.is_none());
        // First context mutation. This deliberately retained verification is
        // part of every experimental hit, including any future timing of it.
        context.body_trace = Some(Trace::new());
        for event in events {
            match event {
                ReplayEvent::Ast { node, id } => assert_eq!(context.lower_node_id(node), id),
                ReplayEvent::Synthetic(id) => assert_eq!(context.next_id(), id),
                ReplayEvent::Bind { node, local } => context.insert_body_binding(node, local),
            }
        }
        let value = cold::Builder { arena: context.arena, spans: context.span_lowerer() }.expr(&body.value);
        let trace = context.body_trace.take().expect("HIR body replay lost its trace");
        let actual = trace.finish(candidate, body.start, body.end, value.hir_id)
            .expect("HIR body replay produced an invalid trace");
        assert_eq!(&actual, checked.journal(), "HIR body replay journal mismatch");
        // Post-effect verification can fail only as an internal invariant. No
        // Option escapes commit and stock lowering is never retried here.
        let current = Current::new(candidate, body.start, &checked.prefix_bindings, &checked)
            .expect("HIR body replay lost its current input");
        let actual = capture::capture(candidate, &current, &value)
            .and_then(|tree| validate::check(tree, &current))
            .expect("HIR body replay produced an invalid tree");
        assert_eq!(actual.tree(), &body.expected, "HIR body replay tree mismatch");
        expected_exit.assert_matches(context);
        assert_eq!(context.curr_owner.item_local_id_counter.as_u32(), body.end);
        value
    }
}

fn ready<'context, 'candidate, 'ast, 'hir>(context: &'context mut crate::LoweringContext<'ast, 'hir>,
    candidate: &'candidate Candidate, key: &[u8], frame: &Frame) -> Option<ReadyHit<'context, 'candidate, 'ast, 'hir>> {
    if !context.tcx.sess.opts.unstable_opts.hir_body_cache_reuse
        || context.tcx.sess.opts.incremental.is_none() || context.body_trace.is_some()
        || context.body_candidate.is_some() || candidate.owner != context.curr_owner.owner_id
        || candidate.context_identity != [context.tcx.sess as *const _ as usize,
            context.arena as *const _ as usize, context.resolver as *const _ as usize]
        || entry::bind(context, &candidate.key)?.as_slice() != key { return None; }
    // The gate/resolver Candidate and entry key were produced in this normal
    // parsing/expansion/resolution invocation. Storage validates that exact key
    // and policy, not just a tree checksum or an old-session pointer identity.
    let payload = storage::read_record(context.tcx.incr_comp_session?, candidate.cache_policy, &candidate.cache_owner, key)?;
    let checked = journal::check(payload.journal,
        &journal::Entry { start: frame.start, nodes: &candidate.nodes, prefix_bindings: &frame.prefix })?;
    let (body, events, expected_exit) = {
        let current = Current::new(candidate, frame.start, &frame.prefix, &checked)?;
        let tree = validate::check(payload.tree, &current)?;
        let prepared = prepare(&tree, &current)?;
        let (events, expected_exit) = frame.replay_plan(context, candidate, &checked)?;
        // Move only owned converted values. No Current/CheckedTree reference is
        // retained, extended or placed next to its owner in a self-reference.
        let PreparedBody { current: _, body } = prepared;
        (body, events, expected_exit)
    };
    Some(ReadyHit { context, candidate, checked, body, events, expected_exit })
}

pub(super) fn try_reuse<'hir>(context: &mut crate::LoweringContext<'_, 'hir>,
    candidate: &Candidate, key: &[u8], frame: &Frame) -> Option<hir::Expr<'hir>> {
    let ready = ready(context, candidate, key, frame)?;
    Some(ready.commit())
}
