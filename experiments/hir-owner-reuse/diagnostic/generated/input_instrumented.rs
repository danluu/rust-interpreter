//! Conservative expanded/resolved-input gate for owner HIR reuse.

use rustc_ast as ast;
use rustc_ast::node_id::{NodeMap, NodeSet};
use rustc_hir as hir;
use rustc_hir::def::Res;
use rustc_middle::middle::resolve::ResolverAstLowering;
use rustc_middle::ty::TyCtxt;
use rustc_macros::Encodable;
use rustc_span::def_id::{DefPathHash, LocalDefId};
use rustc_span::{Ident, Span, StableSourceFileId, SyntaxContext, DUMMY_SP};

#[derive(Debug, PartialEq, Eq, Encodable)]
pub(super) enum SpanKey {
    Dummy,
    Relative { lo: u32, hi: u32 },
}

#[derive(Debug, PartialEq, Eq, Encodable)]
pub(super) enum Resolution {
    Primitive(hir::PrimTy),
    Local(u32),
}

#[derive(Debug, PartialEq, Eq, Encodable)]
pub(super) enum Atom {
    Tag(&'static str),
    Flag(bool),
    Count(usize),
    Text(String),
    Node(u32),
    Span(SpanKey),
    Res(Option<Resolution>),
}

/// Equality covers the entire accepted AST and every resolution entry for its nodes.
/// Storage adds compiler/codec/options identity outside this expanded/resolved-input key.
#[derive(Debug, PartialEq, Eq, Encodable)]
pub(super) struct ResolvedInput {
    pub owner: DefPathHash,
    pub file: StableSourceFileId,
    pub source: String,
    pub atoms: Vec<Atom>,
}

pub(super) struct Probe {
    pub input: ResolvedInput,
    pub current_owner: LocalDefId,
    pub current_span: Span,
}

struct Walk<'a, 'tcx> {
    resolver: &'a ResolverAstLowering<'tcx>,
    base: Span,
    atoms: Vec<Atom>,
    nodes: NodeMap<u32>,
    ordered_nodes: Vec<ast::NodeId>,
    bindings: NodeSet,
}

impl<'a, 'tcx> Walk<'a, 'tcx> {
    fn tag(&mut self, value: &'static str) { self.atoms.push(Atom::Tag(value)); }
    fn flag(&mut self, value: bool) { self.atoms.push(Atom::Flag(value)); }
    fn count(&mut self, value: usize) { self.atoms.push(Atom::Count(value)); }

    fn span(&mut self, span: Span) -> Option<()> {
        let key = if span == DUMMY_SP {
            SpanKey::Dummy
        } else {
            if span.ctxt() != SyntaxContext::root() || span.parent().is_some()
                || !self.base.contains(span)
            {
                return diagnostic_reject(73);
            }
            SpanKey::Relative {
                lo: (span.lo() - self.base.lo()).0,
                hi: (span.hi() - self.base.lo()).0,
            }
        };
        self.atoms.push(Atom::Span(key));
        Some(())
    }

    fn node(&mut self, id: ast::NodeId) -> Option<()> {
        if id == ast::DUMMY_NODE_ID || self.nodes.contains_key(&id)
            || self.ordered_nodes.len() >= 512 { return diagnostic_reject(86); }
        let slot = u32::try_from(self.ordered_nodes.len()).ok().or_else(|| diagnostic_reject(87))?;
        self.nodes.insert(id, slot);
        self.ordered_nodes.push(id);
        self.atoms.push(Atom::Node(slot));
        Some(())
    }

    fn ident(&mut self, ident: Ident) -> Option<()> {
        if ident.name.as_str().len() > 512 { return diagnostic_reject(95); }
        self.atoms.push(Atom::Text(ident.name.as_str().to_owned()));
        self.span(ident.span)
    }

    fn path(&mut self, path: &ast::Path) -> Option<()> {
        let ast::Path { span, segments } = path;
        let [segment] = segments.as_slice() else { return diagnostic_reject(102); };
        let ast::PathSegment { ident, id, args } = segment;
        if args.is_some() { return diagnostic_reject(104); }
        self.span(*span).or_else(|| diagnostic_reject(105))?;
        self.node(*id).or_else(|| diagnostic_reject(106))?;
        self.ident(*ident)
    }

    fn ty(&mut self, ty: &ast::Ty) -> Option<()> {
        let ast::Ty { id, kind, span } = ty;
        let ast::TyKind::Path(None, path) = kind else { return diagnostic_reject(112); };
        let Some(Res::PrimTy(primitive)) = self.resolver.partial_res_map.get(id).or_else(|| diagnostic_reject(113))?.full_res()
            else { return diagnostic_reject(114); };
        if matches!(primitive, hir::PrimTy::Str) { return diagnostic_reject(115); }
        self.tag("primitive-type");
        self.node(*id).or_else(|| diagnostic_reject(117))?;
        self.span(*span).or_else(|| diagnostic_reject(118))?;
        self.path(path)
    }

    fn pat(&mut self, pat: &ast::Pat) -> Option<()> {
        let ast::Pat { id, kind, span } = pat;
        self.node(*id).or_else(|| diagnostic_reject(124))?;
        self.span(*span).or_else(|| diagnostic_reject(125))?;
        match kind {
            ast::PatKind::Wild => self.tag("wild"),
            ast::PatKind::Ident(mode, ident, None) if *mode == hir::BindingMode::NONE => {
                let Some(Res::Local(binding)) = self.resolver.partial_res_map.get(id).or_else(|| diagnostic_reject(129))?.full_res()
                    else { return diagnostic_reject(130); };
                if binding != *id { return diagnostic_reject(131); }
                self.bindings.insert(*id);
                self.tag("immutable-binding");
                self.ident(*ident).or_else(|| diagnostic_reject(134))?;
            }
            _ => return diagnostic_reject(136),
        }
        Some(())
    }

    fn expr(&mut self, expr: &ast::Expr) -> Option<()> {
        let ast::Expr { id, kind, span, attrs, tokens } = expr;
        if !attrs.is_empty() || tokens.is_some() { return diagnostic_reject(143); }
        self.node(*id).or_else(|| diagnostic_reject(144))?;
        self.span(*span).or_else(|| diagnostic_reject(145))?;
        match kind {
            ast::ExprKind::Lit(lit) => {
                if lit.symbol.as_str().len() > 65_536 { return diagnostic_reject(148); }
                let kind = match lit.kind {
                    ast::token::LitKind::Bool => "bool",
                    ast::token::LitKind::Byte => "byte",
                    ast::token::LitKind::Char => "char",
                    ast::token::LitKind::Integer => "integer",
                    ast::token::LitKind::Float => "float",
                    _ => return diagnostic_reject(155),
                };
                // The original error-emitting lower_lit remains responsible for rejected tokens.
                if !matches!(ast::LitKind::from_token_lit(*lit).ok().or_else(|| diagnostic_reject(158))?,
                    ast::LitKind::Bool(..) | ast::LitKind::Byte(..) | ast::LitKind::Char(..)
                    | ast::LitKind::Int(..) | ast::LitKind::Float(..)) { return diagnostic_reject(160); }
                self.tag("literal");
                self.tag(kind);
                self.atoms.push(Atom::Text(lit.symbol.as_str().to_owned()));
                self.flag(lit.suffix.is_some());
                if let Some(suffix) = lit.suffix {
                    self.atoms.push(Atom::Text(suffix.as_str().to_owned()));
                }
            }
            ast::ExprKind::Path(None, path) => {
                let Some(Res::Local(_)) = self.resolver.partial_res_map.get(id).or_else(|| diagnostic_reject(170))?.full_res()
                    else { return diagnostic_reject(171); };
                self.tag("local-path");
                self.path(path).or_else(|| diagnostic_reject(173))?;
            }
            ast::ExprKind::Unary(op @ (ast::UnOp::Not | ast::UnOp::Neg), value) => {
                self.tag(match op { ast::UnOp::Not => "not", _ => "neg" });
                self.expr(value).or_else(|| diagnostic_reject(177))?;
            }
            ast::ExprKind::Binary(op, left, right) => {
                self.tag("binary");
                self.atoms.push(Atom::Text(op.node.as_str().to_owned()));
                self.span(op.span).or_else(|| diagnostic_reject(182))?;
                self.expr(left).or_else(|| diagnostic_reject(183))?;
                self.expr(right).or_else(|| diagnostic_reject(184))?;
            }
            ast::ExprKind::Paren(value) => { self.tag("paren"); self.expr(value).or_else(|| diagnostic_reject(186))?; }
            ast::ExprKind::Block(block, None) => { self.tag("block-expr"); self.block(block).or_else(|| diagnostic_reject(187))?; }
            ast::ExprKind::Ret(value) => {
                self.tag("return");
                self.flag(value.is_some());
                if let Some(value) = value { self.expr(value).or_else(|| diagnostic_reject(191))?; }
            }
            ast::ExprKind::Tup(values) if values.is_empty() => self.tag("unit"),
            _ => return diagnostic_reject(194),
        }
        Some(())
    }

    fn block(&mut self, block: &ast::Block) -> Option<()> {
        let ast::Block { stmts, id, rules, span } = block;
        if !matches!(rules, ast::BlockCheckMode::Default) { return diagnostic_reject(201); }
        self.node(*id).or_else(|| diagnostic_reject(202))?;
        self.span(*span).or_else(|| diagnostic_reject(203))?;
        self.count(stmts.len());
        for stmt in stmts {
            let ast::Stmt { id, kind, span } = stmt;
            self.node(*id).or_else(|| diagnostic_reject(207))?;
            self.span(*span).or_else(|| diagnostic_reject(208))?;
            match kind {
                ast::StmtKind::Let(local) => {
                    let ast::Local { id, super_, pat, ty, kind, span, colon_sp, attrs, tokens } = &**local;
                    if super_.is_some() || !attrs.is_empty() || tokens.is_some() { return diagnostic_reject(212); }
                    self.tag("let");
                    self.node(*id).or_else(|| diagnostic_reject(214))?;
                    self.span(*span).or_else(|| diagnostic_reject(215))?;
                    self.flag(colon_sp.is_some());
                    if let Some(span) = colon_sp { self.span(*span).or_else(|| diagnostic_reject(217))?; }
                    self.flag(ty.is_some());
                    if let Some(ty) = ty { self.ty(ty).or_else(|| diagnostic_reject(219))?; }
                    match kind {
                        ast::LocalKind::Decl => self.tag("uninitialized"),
                        ast::LocalKind::Init(expr) => { self.tag("initialized"); self.expr(expr).or_else(|| diagnostic_reject(222))?; }
                        _ => return diagnostic_reject(223),
                    }
                    self.pat(pat).or_else(|| diagnostic_reject(225))?;
                }
                ast::StmtKind::Expr(expr) => { self.tag("expr-stmt"); self.expr(expr).or_else(|| diagnostic_reject(227))?; }
                ast::StmtKind::Semi(expr) => { self.tag("semi-stmt"); self.expr(expr).or_else(|| diagnostic_reject(228))?; }
                ast::StmtKind::Empty => self.tag("empty-stmt"),
                _ => return diagnostic_reject(230),
            }
        }
        Some(())
    }

    fn resolutions(&mut self) -> Option<()> {
        self.tag("all-current-node-resolutions");
        self.count(self.ordered_nodes.len());
        for node in &self.ordered_nodes {
            let res = match self.resolver.partial_res_map.get(node) {
                None => None,
                Some(partial) => Some(match partial.full_res().or_else(|| diagnostic_reject(242))? {
                    Res::PrimTy(primitive) => Resolution::Primitive(primitive),
                    Res::Local(binding) if self.bindings.contains(&binding) =>
                        Resolution::Local(*self.nodes.get(&binding).or_else(|| diagnostic_reject(245))?),
                    _ => return diagnostic_reject(246),
                }),
            };
            self.atoms.push(Atom::Res(res));
        }
        Some(())
    }
}

/// Call only for AstOwner::Item, before taking the usual with_lctx path.
/// None means ordinary lowering, with no retry and no side-effect suppression.
pub(super) fn probe<'tcx>(
    tcx: TyCtxt<'tcx>, resolver: &ResolverAstLowering<'tcx>, item: &ast::Item,
) -> Option<Probe> {
    if tcx.incr_comp_session.is_none() || tcx.dcx().has_errors().is_some() { return diagnostic_reject(260); }
    let ast::Item { attrs, id, span, vis, kind, tokens } = item;
    if !attrs.is_empty() || tokens.is_some() || *span == DUMMY_SP
        || span.ctxt() != SyntaxContext::root() || span.parent().is_some() { return diagnostic_reject(263); }
    let ast::ItemKind::Fn(function) = kind else { return diagnostic_reject(264); };
    let ast::Fn { defaultness, ident, generics, sig, contract, define_opaque, body, eii_impl } = &**function;
    if !matches!(defaultness, ast::Defaultness::Implicit)
        || contract.is_some() || define_opaque.is_some() || eii_impl.is_some() { return diagnostic_reject(267); }
    let ast::FnSig { header, decl, span: sig_span } = sig;
    let ast::FnHeader { constness, coroutine_marker, safety, ext } = header;
    if !matches!(constness, ast::Const::No) || coroutine_marker.is_some()
        || !matches!(safety, ast::Safety::Default) || !matches!(ext, ast::Extern::None) { return diagnostic_reject(271); }
    let ast::Generics { params, where_clause, span: generics_span } = generics;
    let ast::WhereClause { has_where_token, predicates, span: where_span } = where_clause;
    if !params.is_empty() || *has_where_token || !predicates.is_empty() { return diagnostic_reject(274); }
    let owner = resolver.owners.get(id).or_else(|| diagnostic_reject(275))?;
    if owner.id != *id || !owner.node_id_to_def_id.is_empty() || !owner.label_res_map.is_empty()
        || !owner.lifetimes_res_map.is_empty() || !owner.trait_map.is_empty()
        || !owner.import_res.is_empty() || !owner.extra_lifetime_params_map.is_empty() { return diagnostic_reject(278); }
    let file = tcx.sess.source_map().lookup_source_file(span.lo());
    if !file.contains(span.hi()) || (span.hi() - span.lo()).0 > 65_536 { return diagnostic_reject(280); }
    let source = tcx.sess.source_map().span_to_snippet(*span).ok().or_else(|| diagnostic_reject(281))?;
    let mut walk = Walk { resolver, base: *span, atoms: Vec::new(), nodes: NodeMap::default(),
        ordered_nodes: Vec::new(), bindings: NodeSet::default() };
    walk.tag("resolved-scalar-owner-v1");
    walk.node(*id).or_else(|| diagnostic_reject(285))?;
    walk.span(*span).or_else(|| diagnostic_reject(286))?;
    let ast::Visibility { kind: vis_kind, span: vis_span } = vis;
    match vis_kind {
        ast::VisibilityKind::Inherited => walk.tag("inherited-vis"),
        ast::VisibilityKind::Public => walk.tag("public-vis"),
        _ => return diagnostic_reject(291),
    }
    walk.span(*vis_span).or_else(|| diagnostic_reject(293))?;
    walk.ident(*ident).or_else(|| diagnostic_reject(294))?;
    walk.span(*sig_span).or_else(|| diagnostic_reject(295))?;
    walk.span(*generics_span).or_else(|| diagnostic_reject(296))?;
    walk.span(*where_span).or_else(|| diagnostic_reject(297))?;
    walk.flag(owner.lifetime_elision_allowed);
    let ast::FnDecl { inputs, output } = &**decl;
    walk.count(inputs.len());
    for param in inputs {
        let ast::Param { attrs, ty, pat, id, span, is_placeholder } = param;
        if !attrs.is_empty() || *is_placeholder { return diagnostic_reject(303); }
        walk.node(*id).or_else(|| diagnostic_reject(304))?;
        walk.span(*span).or_else(|| diagnostic_reject(305))?;
        walk.ty(ty).or_else(|| diagnostic_reject(306))?;
        walk.pat(pat).or_else(|| diagnostic_reject(307))?;
    }
    match output {
        ast::FnRetTy::Default(span) => { walk.tag("default-return"); walk.span(*span).or_else(|| diagnostic_reject(310))?; }
        ast::FnRetTy::Ty(ty) => { walk.tag("typed-return"); walk.ty(ty).or_else(|| diagnostic_reject(311))?; }
    }
    walk.block(body.as_deref().or_else(|| diagnostic_reject(313))?).or_else(|| diagnostic_reject(313))?;
    walk.resolutions().or_else(|| diagnostic_reject(314))?;
    Some(Probe {
        input: ResolvedInput { owner: tcx.def_path_hash(owner.def_id.to_def_id()),
            file: file.stable_id, source, atoms: walk.atoms },
        current_owner: owner.def_id,
        current_span: *span,
    })
}

std::thread_local! {
    static DIAGNOSTIC_REJECTION: std::cell::Cell<Option<u32>> = const { std::cell::Cell::new(None) };
}
fn diagnostic_reject<T>(line: u32) -> Option<T> {
    DIAGNOSTIC_REJECTION.with(|value| { if value.get().is_none() { value.set(Some(line)); } });
    None
}
pub(super) fn diagnostic_reset() { DIAGNOSTIC_REJECTION.with(|value| value.set(None)); }
pub(super) fn diagnostic_reason() -> Option<u32> { DIAGNOSTIC_REJECTION.with(|value| value.get()) }
