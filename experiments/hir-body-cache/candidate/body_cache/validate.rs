//! Fallible wire-tree closure checks against the actual allocation journal and
//! freshly resolved input. Never allocates HIR, interns symbols or mutates tcx.
use std::collections::{BTreeMap, BTreeSet};
use rustc_hir::{self as hir, def::Res};
use super::{Candidate, journal, kinds::{self, Kind}, wire as w};

/// Current-session identities are constructed only after journal range checks.
/// They are never persisted. Input indices address the exact keyed resolver
/// input, not an unchecked DefId decoded from a previous compiler invocation.
pub(super) struct Current<'a> {
    pub owner: hir::OwnerId,
    pub start: u32,
    pub source: &'a str,
    pub source_start: u32,
    pub source_end: u32,
    pub source_context: rustc_span::SyntaxContext,
    pub context_identity: [usize; 3],
    pub kinds: &'a [Kind],
    pub journal: &'a journal::Checked,
    pub resolutions: Vec<Option<Res>>,
    pub references: Vec<Option<w::Resolution>>,
    pub locals: BTreeMap<w::LocalRef, hir::HirId>,
    origins: BTreeMap<u32, u32>,
}
impl<'a> Current<'a> {
    pub(super) fn new(candidate: &'a Candidate, start: u32, prefix: &BTreeMap<u32, u32>,
        checked: &'a journal::Checked) -> Option<Self> {
        let invalid = hir::ItemLocalId::INVALID.as_u32();
        if start == 0 || start >= invalid || start != checked.start || *prefix != checked.prefix_bindings
            || checked.end != start.checked_add(checked.journal().end_delta)?
            || checked.end > invalid { return None; }
        let source_start = candidate.current_span.lo().0;
        let source_end = candidate.current_span.hi().0;
        let source_context = candidate.current_span.ctxt();
        if !source_context.is_root()
            || source_end.checked_sub(source_start)? as usize != candidate.source.len() { return None; }
        let mut locals = BTreeMap::new();
        for (&ordinal, &local) in prefix {
            if local == 0 || local >= start { return None; }
            locals.insert(w::LocalRef::Parameter(ordinal), hir::HirId {
                owner: candidate.owner, local_id: hir::ItemLocalId::from_u32(local) });
        }
        for &relative in checked.bindings.values() {
            let local = start.checked_add(relative)?;
            if local >= checked.end { return None; }
            locals.insert(w::LocalRef::Body(relative), hir::HirId {
                owner: candidate.owner, local_id: hir::ItemLocalId::from_u32(local) });
        }
        let binding_ref = |node: rustc_ast::NodeId| -> Option<w::LocalRef> {
            let ordinal = *candidate.ordinals.get(&node)?;
            if prefix.contains_key(&ordinal) { Some(w::LocalRef::Parameter(ordinal)) }
            else { checked.bindings.get(&ordinal).copied().map(w::LocalRef::Body) }
        };
        let mut resolutions = Vec::new(); let mut references = Vec::new();
        for (ordinal, value) in candidate.resolutions.iter().enumerate() {
            let (resolution, reference) = match value {
                None => (None, None),
                Some(Res::Err) => (Some(Res::Err), Some(w::Resolution::MissingSegment)),
                Some(Res::Local(node)) => {
                    let reference = binding_ref(*node)?;
                    (Some(Res::Local(*locals.get(&reference)?)), Some(w::Resolution::Local(reference)))
                }
                Some(value) => (Some(value.apply_id(|_| Err::<hir::HirId, ()>(())).ok()?),
                    Some(w::Resolution::Input(ordinal as u32))),
            };
            resolutions.push(resolution); references.push(reference);
        }
        Some(Self { owner: candidate.owner, start, source: &candidate.source,
            source_start, source_end, source_context, context_identity: candidate.context_identity,
            kinds: &candidate.kinds,
            journal: checked, resolutions, references, locals,
            origins: checked.ast_allocations.iter().map(|(&a, &r)| (r, a)).collect() })
    }
    pub(super) fn origin(&self, relative: u32) -> Option<u32> { self.origins.get(&relative).copied() }
    pub(super) fn resolution(&self, ordinal: u32, segment: bool) -> Option<(Res, w::Resolution)> {
        let res = *self.resolutions.get(ordinal as usize)?;
        let reference = self.references.get(ordinal as usize)?.clone();
        match (res, reference) {
            (Some(Res::Err), Some(w::Resolution::MissingSegment)) | (None, None) if segment =>
                Some((Res::Err, w::Resolution::MissingSegment)),
            (Some(Res::Err), _) | (None, _) => None,
            (Some(res), Some(reference)) => Some((res, reference)),
            _ => None,
        }
    }
}

/// Opaque proof of tree/ID/reference closure. It deliberately has no direct
/// materializer or public constructor. Cold stock lowering remains the semantic producer.
pub(super) struct CheckedTree {
    tree: w::BodyTree,
    _current_resolutions: BTreeMap<u32, Res>,
    _current_locals: BTreeMap<w::LocalRef, hir::HirId>,
}
impl CheckedTree { pub(super) fn tree(&self) -> &w::BodyTree { &self.tree } }

pub(super) fn span(value: &w::SourceSpan, source: &str) -> Option<()> {
    if let w::SourceSpan::Relative { lo, hi } = *value {
        if lo > hi || hi as usize > source.len() || !source.is_char_boundary(lo as usize)
            || !source.is_char_boundary(hi as usize) { return None; }
    }
    Some(())
}
struct Check<'a, 'b> {
    current: &'a Current<'b>, seen: BTreeSet<u32>, bindings: BTreeSet<u32>,
    resolutions: BTreeMap<u32, Res>, locals: BTreeMap<w::LocalRef, hir::HirId>,
}
impl Check<'_, '_> {
    fn node(&mut self, n: &w::Node, kind: Kind, synthetic_block: bool) -> Option<Option<u32>> {
        span(&n.span, self.current.source)?;
        if n.relative >= self.current.journal.journal().end_delta || !self.seen.insert(n.relative) {
            return None;
        }
        let origin = self.current.origin(n.relative);
        match origin {
            Some(ordinal) if self.current.kinds.get(ordinal as usize) == Some(&kind) => (),
            None if synthetic_block && kind == Kind::Expression(kinds::Expr::Block) => (),
            _ => return None,
        }
        Some(origin)
    }
    fn ident(&self, ident: &w::Ident) -> Option<()> {
        if ident.text.len() > 4096 { return None; }
        span(&ident.span, self.current.source)
    }
    fn reference(&mut self, reference: &w::LocalRef, use_at: Option<u32>) -> Option<()> {
        let current = *self.current.locals.get(reference)?;
        if let (w::LocalRef::Body(binding), Some(use_at)) = (reference, use_at) {
            if *binding >= use_at { return None; }
        }
        self.locals.insert(reference.clone(), current); Some(())
    }
    fn resolution(&mut self, value: &w::Resolution, origin: u32, segment: bool, at: u32) -> Option<()> {
        let (current, expected) = self.current.resolution(origin, segment)?;
        if *value != expected { return None; }
        if let w::Resolution::Local(reference) = value { self.reference(reference, Some(at))?; }
        self.resolutions.insert(origin, current); Some(())
    }
    fn segment(&mut self, s: &w::Segment) -> Option<()> {
        let origin = self.node(&w::Node { relative: s.relative, span: s.ident.span.clone() }, Kind::Segment, false)??;
        self.ident(&s.ident)?;
        self.resolution(&s.resolution, origin, true, s.relative)
    }
    fn pattern(&mut self, p: &w::Pattern) -> Option<()> {
        if !p.default_binding_modes { return None; }
        let binding = matches!(p.kind, w::PatternKind::Binding { .. });
        let origin = self.node(&p.node, Kind::Pattern { binding }, false)??;
        match &p.kind {
            w::PatternKind::Wild => (),
            w::PatternKind::Binding { target, ident, .. } => {
                if *target != w::LocalRef::Body(p.node.relative)
                    || self.current.journal.bindings.get(&origin) != Some(&p.node.relative)
                    || !self.bindings.insert(origin) { return None; }
                self.ident(ident)?; self.reference(target, None)?;
            }
        }
        Some(())
    }
    fn literal(&self, value: &w::Literal) -> Option<()> {
        let valid = match value {
            w::Literal::String(v, _) => v.len() <= 131072,
            w::Literal::Bytes(v, _) => v.len() <= 131072,
            w::Literal::CString(v, _) => v.len() <= 131073 && v.last() == Some(&0)
                && !v[..v.len().saturating_sub(1)].contains(&0),
            w::Literal::Integer(v, suffix) => v.parse::<u128>().is_ok_and(|n| n.to_string() == *v)
                && suffix.as_deref().is_none_or(w::integer_type),
            // Keep the actual lexer float spelling; do not round through f64.
            w::Literal::Float(v, suffix) => float_spelling(v, suffix.is_some())
                && suffix.as_deref().is_none_or(w::float_type),
            w::Literal::Bool(_) | w::Literal::Byte(_) | w::Literal::Char(_) => true,
        };
        valid.then_some(())
    }
    fn expr(&mut self, e: &w::Expr, depth: usize, synthetic_block: bool) -> Option<()> {
        if depth >= 64 { return None; }
        use kinds::Expr as K; use w::ExprKind as E;
        let kind = match &e.kind {
            E::Array(_) => K::Array, E::Tuple(_) => K::Tuple, E::Literal { .. } => K::Literal,
            E::Path(_) => K::Path, E::Call { .. } => K::Call, E::Method { .. } => K::Method,
            E::Unary(..) => K::Unary, E::Binary { .. } => K::Binary, E::Block(_) => K::Block,
            E::If { .. } => K::If, E::Assign { .. } => K::Assign, E::AssignOp { .. } => K::AssignOp,
            E::Field(..) => K::Field, E::Index { .. } => K::Index, E::Borrow { .. } => K::Borrow,
            E::Return(_) => K::Return,
        };
        let origin = self.node(&e.node, Kind::Expression(kind), synthetic_block)?;
        // Root and then-block have no AST Expr. Every ordinary child does.
        if synthetic_block != origin.is_none() { return None; }
        match &e.kind {
            E::Array(v) | E::Tuple(v) => for e in v { self.expr(e, depth + 1, false)?; },
            E::Literal { span: s, value } => { span(s, self.current.source)?; self.literal(value)?; }
            E::Path(p) => {
                span(&p.span, self.current.source)?;
                self.resolution(&p.resolution, origin?, false, e.node.relative)?;
                if p.segments.is_empty() { return None; }
                for s in &p.segments { self.segment(s)?; }
            }
            E::Call { function, arguments } => {
                self.expr(function, depth + 1, false)?;
                for a in arguments { self.expr(a, depth + 1, false)?; }
            }
            E::Method { segment, receiver, arguments, span: s } => {
                self.segment(segment)?; self.expr(receiver, depth + 1, false)?;
                for a in arguments { self.expr(a, depth + 1, false)?; }
                span(s, self.current.source)?;
            }
            E::Unary(_, v) | E::Borrow { value: v, .. } => self.expr(v, depth + 1, false)?,
            E::Binary { operation, span: s, left, right } |
            E::AssignOp { operation, span: s, left, right } => {
                if !(if matches!(e.kind, E::Binary { .. }) { w::binary(operation) } else { w::assignment(operation) }) {
                    return None;
                }
                span(s, self.current.source)?; self.expr(left, depth + 1, false)?; self.expr(right, depth + 1, false)?;
            }
            E::Block(block) => self.block(block, depth + 1)?,
            E::If { condition, then, otherwise } => {
                self.expr(condition, depth + 1, false)?;
                if !matches!(then.kind, E::Block(_)) { return None; }
                self.expr(then, depth + 1, true)?;
                if let Some(e) = otherwise {
                    if !matches!(e.kind, E::Block(_) | E::If { .. }) { return None; }
                    self.expr(e, depth + 1, false)?;
                }
            }
            E::Assign { left, right, span: s } => {
                span(s, self.current.source)?; self.expr(left, depth + 1, false)?; self.expr(right, depth + 1, false)?;
            }
            E::Field(v, ident) => { self.expr(v, depth + 1, false)?; self.ident(ident)?; }
            E::Index { value, index, span: s } => {
                self.expr(value, depth + 1, false)?; self.expr(index, depth + 1, false)?; span(s, self.current.source)?;
            }
            E::Return(v) => if let Some(v) = v { self.expr(v, depth + 1, false)?; },
        }
        Some(())
    }
    fn block(&mut self, b: &w::Block, depth: usize) -> Option<()> {
        if depth >= 64 || b.targeted_by_break { return None; }
        self.node(&b.node, Kind::Block, false)??;
        for s in &b.statements {
            let kind = match &s.kind {
                w::StatementKind::Let(_) => kinds::Statement::Let,
                w::StatementKind::Expr(_) => kinds::Statement::Expr,
                w::StatementKind::Semi(_) => kinds::Statement::Semi,
            };
            self.node(&s.node, Kind::Statement(kind), false)??;
            match &s.kind {
                w::StatementKind::Let(l) => {
                    self.node(&l.node, Kind::Local, false)??;
                    if let Some(e) = &l.init { self.expr(e, depth + 1, false)?; }
                    self.pattern(&l.pattern)?;
                }
                w::StatementKind::Expr(e) | w::StatementKind::Semi(e) => self.expr(e, depth + 1, false)?,
            }
        }
        if let Some(e) = &b.tail { self.expr(e, depth + 1, false)?; }
        Some(())
    }
}

pub(super) fn check(tree: w::BodyTree, current: &Current<'_>) -> Option<CheckedTree> {
    if tree.value.node.relative != current.journal.journal().root_relative
        || !matches!(tree.value.kind, w::ExprKind::Block(_)) { return None; }
    let mut c = Check { current, seen: BTreeSet::new(), bindings: BTreeSet::new(),
        resolutions: BTreeMap::new(), locals: BTreeMap::new() };
    c.expr(&tree.value, 0, true)?;
    let mut order = Order { current, events: Vec::new() };
    order.expr(&tree.value)?;
    if order.events != current.journal.journal().events { return None; }
    if c.seen.len() != current.journal.journal().end_delta as usize
        || c.bindings != current.journal.bindings.keys().copied().collect() { return None; }
    Some(CheckedTree { tree, _current_resolutions: c.resolutions, _current_locals: c.locals })
}

fn float_spelling(value: &str, suffixed: bool) -> bool {
    if value.len() > 131072 { return false; }
    let bytes = value.as_bytes(); let mut i = 0;
    while bytes.get(i).is_some_and(u8::is_ascii_digit) { i += 1; }
    if i == 0 { return false; }
    let mut floating = suffixed;
    if bytes.get(i) == Some(&b'.') {
        floating = true; i += 1;
        while bytes.get(i).is_some_and(u8::is_ascii_digit) { i += 1; }
    }
    if matches!(bytes.get(i), Some(b'e' | b'E')) {
        floating = true; i += 1;
        if matches!(bytes.get(i), Some(b'+' | b'-')) { i += 1; }
        let digits = i;
        while bytes.get(i).is_some_and(u8::is_ascii_digit) { i += 1; }
        if i == digits { return false; }
    }
    floating && i == bytes.len()
}

/// Cross-check the actual allocation/binding call order, independently of the
/// wire's ownership traversal. This emits data only; it never replays effects.
/// In particular synthetic block Expr IDs follow their block, Expr/Semi Stmt
/// IDs follow their expression, and Local IDs follow the initializer.
struct Order<'a, 'b> { current: &'a Current<'b>, events: Vec<journal::Event> }
impl Order<'_, '_> {
    fn allocate(&mut self, relative: u32) {
        self.events.push(journal::Event::Allocate { relative,
            source: self.current.origin(relative).map_or(journal::Allocation::Synthetic, journal::Allocation::Ast) });
    }
    fn expr(&mut self, e: &w::Expr) -> Option<()> {
        let synthetic = self.current.origin(e.node.relative).is_none();
        if !synthetic { self.allocate(e.node.relative); }
        use w::ExprKind as E;
        match &e.kind {
            E::Array(v) | E::Tuple(v) => for e in v { self.expr(e)?; },
            E::Literal { .. } => (),
            E::Path(p) => for s in &p.segments { self.allocate(s.relative); },
            E::Call { function, arguments } => { self.expr(function)?; for a in arguments { self.expr(a)?; } }
            E::Method { segment, receiver, arguments, .. } => {
                self.allocate(segment.relative); self.expr(receiver)?; for a in arguments { self.expr(a)?; }
            }
            E::Unary(_, v) | E::Borrow { value: v, .. } | E::Field(v, _) => self.expr(v)?,
            E::Binary { left, right, .. } | E::AssignOp { left, right, .. } => { self.expr(left)?; self.expr(right)?; }
            // Lowering order (not runtime evaluation order) is LHS then RHS.
            E::Assign { left, right, .. } => { self.expr(left)?; self.expr(right)?; }
            E::Block(b) => self.block(b)?,
            E::If { condition, then, otherwise } => {
                self.expr(condition)?; self.expr(then)?; if let Some(e) = otherwise { self.expr(e)?; }
            }
            E::Index { value, index, .. } => { self.expr(value)?; self.expr(index)?; }
            E::Return(v) => if let Some(v) = v { self.expr(v)?; },
        }
        if synthetic { self.allocate(e.node.relative); }
        Some(())
    }
    fn block(&mut self, b: &w::Block) -> Option<()> {
        self.allocate(b.node.relative);
        for s in &b.statements {
            match &s.kind {
                w::StatementKind::Let(l) => {
                    self.allocate(s.node.relative);
                    if let Some(e) = &l.init { self.expr(e)?; }
                    self.allocate(l.node.relative); self.allocate(l.pattern.node.relative);
                    if matches!(l.pattern.kind, w::PatternKind::Binding { .. }) {
                        self.events.push(journal::Event::Bind { ast: self.current.origin(l.pattern.node.relative)?,
                            relative: l.pattern.node.relative });
                    }
                }
                w::StatementKind::Expr(e) | w::StatementKind::Semi(e) => { self.expr(e)?; self.allocate(s.node.relative); }
            }
        }
        if let Some(e) = &b.tail { self.expr(e)?; }
        Some(())
    }
}

#[cfg(test)]
pub(super) mod tests {
    use super::*;
    fn node(relative: u32) -> w::Node { w::Node { relative, span: w::SourceSpan::Relative { lo: 0, hi: 2 } } }
    pub(in crate::body_cache) fn tree() -> w::BodyTree {
        w::BodyTree { value: w::Expr { node: node(2), kind: w::ExprKind::Block(w::Block {
            node: node(0), statements: vec![], tail: Some(Box::new(w::Expr { node: node(1),
                kind: w::ExprKind::Literal { span: w::SourceSpan::Relative { lo: 0, hi: 2 }, value: w::Literal::Integer("42".into(), None) } })),
            rules: w::BlockRules::Default, targeted_by_break: false }) } }
    }
    pub(in crate::body_cache) fn checked() -> journal::Checked {
        let nodes = vec![journal::Node { body: true, binding: false, traits: false }; 2];
        journal::check(journal::Journal { events: vec![
            journal::Event::Allocate { source: journal::Allocation::Ast(0), relative: 0 },
            journal::Event::Allocate { source: journal::Allocation::Ast(1), relative: 1 },
            journal::Event::Allocate { source: journal::Allocation::Synthetic, relative: 2 },
        ], end_delta: 3, root_relative: 2 }, &journal::Entry { start: 3, nodes: &nodes, prefix_bindings: &BTreeMap::new() }).unwrap()
    }
    pub(in crate::body_cache) fn current(checked: &journal::Checked) -> Current<'_> {
        Current { owner: hir::OwnerId { def_id: rustc_span::def_id::CRATE_DEF_ID }, start: 3, source: "42é",
            source_start: 100, source_end: 104, source_context: rustc_span::SyntaxContext::root(),
            context_identity: [0; 3],
            kinds: &[Kind::Block, Kind::Expression(kinds::Expr::Literal)], journal: checked,
            resolutions: vec![None, None], references: vec![None, None], locals: BTreeMap::new(),
            origins: BTreeMap::from([(0, 0), (1, 1)]) }
    }
    #[test]
    fn complete_tree_ids_and_exclusive_root_are_required() {
        let checked = checked(); let current = current(&checked);
        assert!(check(tree(), &current).is_some());
        let mut duplicate = tree();
        let w::ExprKind::Block(b) = &mut duplicate.value.kind else { unreachable!() };
        b.tail.as_mut().unwrap().node.relative = 0;
        assert!(check(duplicate, &current).is_none());
        let mut missing = tree();
        let w::ExprKind::Block(b) = &mut missing.value.kind else { unreachable!() };
        b.tail = None;
        assert!(check(missing, &current).is_none());
        let mut outside = tree(); outside.value.node.relative = 3;
        assert!(check(outside, &current).is_none());
        let mut wrong_kind = tree();
        let w::ExprKind::Block(b) = &mut wrong_kind.value.kind else { unreachable!() };
        b.tail.as_mut().unwrap().kind = w::ExprKind::Tuple(vec![]);
        assert!(check(wrong_kind, &current).is_none());
    }
    #[test]
    fn spans_reject_split_utf8_reversal_and_outside_owner() {
        for (lo, hi) in [(0, 0), (0, 2), (2, 4), (4, 4)] {
            assert!(span(&w::SourceSpan::Relative { lo, hi }, "42é").is_some());
        }
        for (lo, hi) in [(0, 3), (3, 4), (4, 2), (0, 5), (u32::MAX, u32::MAX)] {
            assert!(span(&w::SourceSpan::Relative { lo, hi }, "42é").is_none());
        }
    }
    #[test]
    fn references_are_current_binding_and_resolution_specific() {
        let checked = checked(); let mut current = current(&checked);
        let local = w::LocalRef::Parameter(7);
        let id = hir::HirId { owner: current.owner, local_id: hir::ItemLocalId::from_u32(1) };
        current.locals.insert(local.clone(), id);
        current.references[1] = Some(w::Resolution::Local(local.clone()));
        current.resolutions[1] = Some(Res::Local(id));
        let mut c = Check { current: &current, seen: BTreeSet::new(), bindings: BTreeSet::new(),
            resolutions: BTreeMap::new(), locals: BTreeMap::new() };
        assert!(c.resolution(&w::Resolution::Local(local), 1, false, 1).is_some());
        assert!(c.resolution(&w::Resolution::Input(1), 1, false, 1).is_none());
        assert!(c.resolution(&w::Resolution::Local(w::LocalRef::Parameter(8)), 1, false, 1).is_none());
        assert!(c.resolution(&w::Resolution::MissingSegment, 0, false, 1).is_none());
        assert!(c.resolution(&w::Resolution::MissingSegment, 0, true, 1).is_some());
        assert!(c.reference(&w::LocalRef::Body(0), Some(1)).is_none());
        drop(c);
        current.references[1] = Some(w::Resolution::Input(1));
        current.resolutions[1] = Some(Res::SelfCtor(rustc_span::def_id::CRATE_DEF_ID.to_def_id()));
        let mut c = Check { current: &current, seen: BTreeSet::new(), bindings: BTreeSet::new(),
            resolutions: BTreeMap::new(), locals: BTreeMap::new() };
        assert!(c.resolution(&w::Resolution::Input(1), 1, false, 1).is_some());
        assert!(c.resolution(&w::Resolution::Input(0), 1, false, 1).is_none());
    }
    #[test]
    fn journal_order_cannot_be_changed_while_preserving_tree_ids() {
        let mut checked = checked();
        // Both journals separately pass event-layout validation, but the tree
        // requires its Block allocation before its literal.
        let nodes = vec![journal::Node { body: true, binding: false, traits: false }; 2];
        let mut altered = checked.journal().clone();
        altered.events[0] = journal::Event::Allocate { source: journal::Allocation::Ast(1), relative: 0 };
        altered.events[1] = journal::Event::Allocate { source: journal::Allocation::Ast(0), relative: 1 };
        checked = journal::check(altered, &journal::Entry { start: 3, nodes: &nodes, prefix_bindings: &BTreeMap::new() }).unwrap();
        let mut current = current(&checked); current.origins = BTreeMap::from([(1, 0), (0, 1)]);
        let mut moved = tree();
        let w::ExprKind::Block(b) = &mut moved.value.kind else { unreachable!() };
        b.node.relative = 1; b.tail.as_mut().unwrap().node.relative = 0;
        assert!(check(moved, &current).is_none());
    }
    #[test]
    fn ordinary_assignment_uses_lhs_then_rhs_lowering_order() {
        let mut nodes = vec![journal::Node { body: true, binding: false, traits: false }; 6];
        nodes.push(journal::Node { body: false, binding: true, traits: false });
        let mut events: Vec<_> = (0..6).map(|relative| journal::Event::Allocate {
            source: journal::Allocation::Ast(relative), relative }).collect();
        events.push(journal::Event::Allocate { source: journal::Allocation::Synthetic, relative: 6 });
        let checked = journal::check(journal::Journal { events, end_delta: 7, root_relative: 6 },
            &journal::Entry { start: 3, nodes: &nodes, prefix_bindings: &BTreeMap::from([(6, 1)]) }).unwrap();
        let owner = hir::OwnerId { def_id: rustc_span::def_id::CRATE_DEF_ID };
        let parameter = w::LocalRef::Parameter(6);
        let id = hir::HirId { owner, local_id: hir::ItemLocalId::from_u32(1) };
        let current = Current { owner, start: 3, source: "42é", journal: &checked,
            source_start: 100, source_end: 104, source_context: rustc_span::SyntaxContext::root(),
            context_identity: [0; 3],
            kinds: &[Kind::Block, Kind::Expression(kinds::Expr::Assign), Kind::Expression(kinds::Expr::Path),
                Kind::Segment, Kind::Expression(kinds::Expr::Literal), Kind::Statement(kinds::Statement::Semi),
                Kind::Pattern { binding: true }],
            origins: (0..6).map(|n| (n, n)).collect(),
            locals: BTreeMap::from([(parameter.clone(), id)]),
            resolutions: vec![None, None, Some(Res::Local(id)), None, None, None, Some(Res::Local(id))],
            references: vec![None, None, Some(w::Resolution::Local(parameter.clone())), None, None, None,
                Some(w::Resolution::Local(parameter.clone()))] };
        let span = w::SourceSpan::Relative { lo: 0, hi: 2 };
        let assign = w::Expr { node: node(1), kind: w::ExprKind::Assign {
            left: Box::new(w::Expr { node: node(2), kind: w::ExprKind::Path(w::Path {
                span: span.clone(), resolution: w::Resolution::Local(parameter), segments: vec![w::Segment {
                    relative: 3, ident: w::Ident { text: "x".into(), span: span.clone() },
                    resolution: w::Resolution::MissingSegment, infer_args: true }] }) }),
            right: Box::new(w::Expr { node: node(4), kind: w::ExprKind::Literal {
                span: span.clone(), value: w::Literal::Integer("42".into(), None) } }), span } };
        let value = w::BodyTree { value: w::Expr { node: node(6), kind: w::ExprKind::Block(w::Block {
            node: node(0), statements: vec![w::Statement { node: node(5), kind: w::StatementKind::Semi(assign) }],
            tail: None, rules: w::BlockRules::Default, targeted_by_break: false }) } };
        assert!(check(value, &current).is_some());
    }
    #[test]
    fn typed_literal_domain_is_bounded_without_rounding() {
        for value in ["1.", "1.25", "1e99", "1e-9999", "0001.0"] { assert!(float_spelling(value, false)); }
        assert!(float_spelling("42", true));
        for value in ["", "1", "-1.0", "NaN", "inf", "1..2", "1e", "1e+", "1_2.0"] {
            assert!(!float_spelling(value, false));
        }
    }
}
