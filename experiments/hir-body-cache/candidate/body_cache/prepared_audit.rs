//! Private cold audit. Reconstructed HIR never enters owner indexing or checks.
//! Builder has only arena/span facilities: no ID allocator, map, resolver or tcx.
use super::*;
use rustc_data_structures::packed::Pu128;
use rustc_span::{ByteSymbol, DUMMY_SP, Ident as HirIdent, Span, Symbol, SyntaxContext};
use super::super::{Candidate, capture};

struct Observed<'a> {
    owner: hir::OwnerId,
    counter: u32,
    context_identity: [usize; 3],
    source_start: BytePos,
    source_end: BytePos,
    source: &'a str,
}
fn compatible(prepared: &PreparedBody<'_, '_>, observed: &Observed<'_>) -> bool {
    let current = prepared.current;
    prepared.owner == observed.owner && prepared.owner == current.owner
        && prepared.start == current.start && prepared.end == current.journal.end
        && prepared.end == observed.counter && prepared.source_start == observed.source_start
        && prepared.source_end == observed.source_end && prepared.source == observed.source
        && prepared.source_start.0 == current.source_start && prepared.source_end.0 == current.source_end
        && prepared.source == current.source && current.context_identity == observed.context_identity
}

pub(super) fn audit(lctx: &crate::LoweringContext<'_, '_>, candidate: &Candidate,
    expected: &CheckedTree, prepared: PreparedBody<'_, '_>) -> Option<()> {
    let current = prepared.current;
    let observed = Observed { owner: lctx.curr_owner.owner_id,
        counter: lctx.curr_owner.item_local_id_counter.as_u32(),
        context_identity: [lctx.tcx.sess as *const _ as usize, lctx.arena as *const _ as usize,
            lctx.resolver as *const _ as usize],
        source_start: candidate.current_span.lo(), source_end: candidate.current_span.hi(),
        source: &candidate.source };
    // All rejection here precedes arena/span/symbol effects. Pointer equality
    // is only an extra cold-call guard, not proof of lifetime or exclusivity.
    // The private caller retains lctx, Candidate and Current lexically, and
    // PreparedBody borrows Current until this audit consumes it.
    if !compatible(&prepared, &observed) || candidate.owner != observed.owner
        || candidate.context_identity != observed.context_identity
        || !candidate.current_span.ctxt().is_root() || lctx.tcx.sess.opts.incremental.is_none()
        || lctx.body_trace.is_some() || prepared.expected != *expected.tree()
        || current_state(current)? != prepared.prefix { return None; }
    let rebuilt = Builder { arena: lctx.arena, spans: lctx.span_lowerer() }.expr(&prepared.value);
    // Fallible validation after allocation is an audit rejection, never a
    // reason to re-lower an already advanced context. No reconstructed node is
    // registered as an owner/body or returned to ordinary compiler queries.
    let recaptured = capture::capture(candidate, current, &rebuilt)?;
    let checked = validate::check(recaptured, current)?;
    (checked.tree() == &prepared.expected).then_some(())
}

struct Builder<'hir> { arena: &'hir hir::Arena<'hir>, spans: crate::SpanLowerer }
impl<'hir> Builder<'hir> {
    fn span(&self, value: &SpanRecipe) -> Span {
        let span = match *value {
            SpanRecipe::Dummy => DUMMY_SP,
            SpanRecipe::Current { owner, lo, hi } => {
                // The sealed constructor/current borrow established this
                // invariant before any materialization; no decoded lookup.
                debug_assert_eq!(owner.def_id, self.spans.def_id);
                Span::new(lo, hi, SyntaxContext::root(), None)
            }
        };
        self.spans.lower(span)
    }
    fn ident(&self, value: &Ident) -> HirIdent {
        let Ident { text, span } = value;
        HirIdent::new(Symbol::intern(text), self.span(span))
    }
    fn segment(&self, value: &Segment) -> hir::PathSegment<'hir> {
        let Segment { id, ident, resolution, infer_args } = value;
        hir::PathSegment { ident: self.ident(ident), hir_id: *id, res: *resolution,
            args: None, infer_args: *infer_args, delegation_child_segment: false }
    }
    fn pattern(&self, value: &Pattern) -> &'hir hir::Pat<'hir> {
        let Pattern { node: Node { id, span }, kind, default_binding_modes } = value;
        let kind = match kind {
            PatternKind::Wild => hir::PatKind::Wild,
            PatternKind::Binding { mode, target, ident } => hir::PatKind::Binding(*mode, *target, self.ident(ident), None),
        };
        self.arena.alloc(hir::Pat { hir_id: *id, kind, span: self.span(span), default_binding_modes: *default_binding_modes })
    }
    fn literal(&self, value: &Literal) -> ast::LitKind {
        use Literal as L; use ast::LitKind as H;
        match value {
            L::String(value, style) => H::Str(Symbol::intern(value), *style),
            L::Bytes(value, style) => H::ByteStr(ByteSymbol::intern(value), *style),
            L::CString(value, style) => H::CStr(ByteSymbol::intern(value), *style),
            L::Bool(value) => H::Bool(*value), L::Byte(value) => H::Byte(*value), L::Char(value) => H::Char(*value),
            L::Integer(value, ty) => H::Int(Pu128(*value), *ty),
            L::Float(value, ty) => H::Float(Symbol::intern(value), *ty),
        }
    }
    fn exprs(&self, values: &[Expr]) -> &'hir [hir::Expr<'hir>] {
        self.arena.alloc_from_iter(values.iter().map(|value| self.expr(value)))
    }
    fn expr_ref(&self, value: &Expr) -> &'hir hir::Expr<'hir> { self.arena.alloc(self.expr(value)) }
    fn optional(&self, value: &Option<Box<Expr>>) -> Option<&'hir hir::Expr<'hir>> {
        value.as_ref().map(|value| self.expr_ref(value))
    }
    fn expr(&self, value: &Expr) -> hir::Expr<'hir> {
        use ExprKind as E; use hir::ExprKind as H;
        let Expr { node: Node { id, span }, kind } = value;
        let kind = match kind {
            E::Array(values) => H::Array(self.exprs(values)), E::Tuple(values) => H::Tup(self.exprs(values)),
            E::Literal { span, value } => H::Lit(hir::Lit { node: self.literal(value), span: self.span(span) }),
            E::Path(Path { span, resolution, segments }) => H::Path(hir::QPath::Resolved(None,
                self.arena.alloc(hir::Path { span: self.span(span), res: *resolution,
                    segments: self.arena.alloc_from_iter(segments.iter().map(|segment| self.segment(segment))) }))),
            E::Call { function, arguments } => H::Call(self.expr_ref(function), self.exprs(arguments)),
            E::Method { segment, receiver, arguments, span } => H::MethodCall(self.arena.alloc(self.segment(segment)),
                self.expr_ref(receiver), self.exprs(arguments), self.span(span)),
            E::Unary(operation, value) => H::Unary(*operation, self.expr_ref(value)),
            E::Binary { operation, span, left, right } => H::Binary(hir::BinOp { node: *operation, span: self.span(span) },
                self.expr_ref(left), self.expr_ref(right)),
            E::Block(block) => H::Block(self.block(block), None),
            E::If { condition, then, otherwise } => H::If(self.expr_ref(condition), self.expr_ref(then), self.optional(otherwise)),
            E::Assign { left, right, span } => H::Assign(self.expr_ref(left), self.expr_ref(right), self.span(span)),
            E::AssignOp { operation, span, left, right } => H::AssignOp(hir::AssignOp { node: *operation, span: self.span(span) },
                self.expr_ref(left), self.expr_ref(right)),
            E::Field(value, ident) => H::Field(self.expr_ref(value), self.ident(ident)),
            E::Index { value, index, span } => H::Index(self.expr_ref(value), self.expr_ref(index), self.span(span)),
            E::Borrow { kind, mutability, value } => H::AddrOf(*kind, *mutability, self.expr_ref(value)),
            E::Return(value) => H::Ret(self.optional(value)),
        };
        hir::Expr { hir_id: *id, kind, span: self.span(span) }
    }
    fn local(&self, value: &Local) -> &'hir hir::LetStmt<'hir> {
        let Local { node: Node { id, span }, pattern, init } = value;
        self.arena.alloc(hir::LetStmt { super_: None, pat: self.pattern(pattern), ty: None,
            init: init.as_ref().map(|value| self.expr_ref(value)), els: None, hir_id: *id,
            span: self.span(span), source: hir::LocalSource::Normal })
    }
    fn statement(&self, value: &Statement) -> hir::Stmt<'hir> {
        let Statement { node: Node { id, span }, kind } = value;
        let kind = match kind {
            StatementKind::Let(local) => hir::StmtKind::Let(self.local(local)),
            StatementKind::Expr(value) => hir::StmtKind::Expr(self.expr_ref(value)),
            StatementKind::Semi(value) => hir::StmtKind::Semi(self.expr_ref(value)),
        };
        hir::Stmt { hir_id: *id, kind, span: self.span(span) }
    }
    fn block(&self, value: &Block) -> &'hir hir::Block<'hir> {
        let Block { node: Node { id, span }, statements, tail, rules, targeted_by_break } = value;
        self.arena.alloc(hir::Block {
            stmts: self.arena.alloc_from_iter(statements.iter().map(|value| self.statement(value))),
            expr: self.optional(tail), hir_id: *id, rules: *rules, span: self.span(span), targeted_by_break: *targeted_by_break })
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use validate::tests::{checked, current, tree};

    #[test]
    fn cold_identity_requires_exact_exit_counter_context_owner_and_source() {
        let journal = checked(); let current = current(&journal);
        let checked = validate::check(tree(), &current).unwrap();
        let prepared = prepare(&checked, &current).unwrap();
        let mut observed = Observed { owner: current.owner, counter: journal.end,
            context_identity: current.context_identity, source_start: BytePos(current.source_start),
            source_end: BytePos(current.source_end), source: current.source };
        assert!(compatible(&prepared, &observed));
        observed.counter = current.start; assert!(!compatible(&prepared, &observed)); observed.counter = journal.end;
        observed.context_identity[0] += 1; assert!(!compatible(&prepared, &observed)); observed.context_identity[0] -= 1;
        observed.source = "43é"; assert!(!compatible(&prepared, &observed)); observed.source = current.source;
        observed.source_start.0 += 1; assert!(!compatible(&prepared, &observed)); observed.source_start.0 -= 1;
        observed.owner = hir::OwnerId { def_id: rustc_span::def_id::LocalDefId {
            local_def_index: rustc_span::def_id::DefIndex::from_u32(1) } };
        assert!(!compatible(&prepared, &observed));
    }

    #[test]
    fn cold_arena_literal_roundtrip_preserves_bytes_suffixes_and_independent_spans() {
        rustc_span::create_default_session_globals_then(|| {
            let journal = checked(); let current = current(&journal);
            let candidate = Candidate { owner: current.owner, body: ast::DUMMY_NODE_ID,
                name: "unit-only".into(), key: vec![], path: std::path::PathBuf::new(), ast_nodes: vec![],
                ordinals: ast::node_id::NodeMap::default(), nodes: vec![], kinds: vec![], resolutions: vec![],
                current_span: Span::new(BytePos(current.source_start), BytePos(current.source_end), SyntaxContext::root(), None),
                source: current.source.into(), input_statistics: [0; 6], context_identity: current.context_identity };
            let arena = hir::Arena::default();
            let builder = Builder { arena: &arena, spans: crate::SpanLowerer { is_incremental: true, def_id: current.owner.def_id } };
            let dummy = builder.span(&SpanRecipe::Dummy);
            assert!(dummy.is_dummy()); assert_eq!(dummy.parent(), Some(current.owner.def_id));
            assert!(dummy.ctxt().is_root());
            for literal in [
                w::Literal::Integer(u128::MAX.to_string(), Some("u128".into())),
                w::Literal::Float("1e-9999".into(), Some("f128".into())),
                w::Literal::String("é\n\0".into(), w::StringStyle::Raw(2)),
                w::Literal::Bytes(vec![255, 0, 127], w::StringStyle::Cooked),
                w::Literal::CString(vec![b'x', 0], w::StringStyle::Raw(1)),
                w::Literal::Bool(true), w::Literal::Byte(255), w::Literal::Char('é'),
            ] {
                let mut wire = tree();
                let w::ExprKind::Block(block) = &mut wire.value.kind else { panic!() };
                let tail = block.tail.as_mut().unwrap();
                tail.node.span = w::SourceSpan::Relative { lo: 0, hi: 4 };
                tail.kind = w::ExprKind::Literal { span: w::SourceSpan::Relative { lo: 2, hi: 4 }, value: literal };
                let checked = validate::check(wire, &current).unwrap();
                let prepared = prepare(&checked, &current).unwrap();
                let rebuilt = builder.expr(&prepared.value);
                let recaptured = capture::capture(&candidate, &current, &rebuilt).unwrap();
                assert_eq!(validate::check(recaptured, &current).unwrap().tree(), checked.tree());
            }
        });
    }
}
