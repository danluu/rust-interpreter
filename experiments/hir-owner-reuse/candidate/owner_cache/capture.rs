use rustc_abi::ExternAbi;
use rustc_ast as ast;
use rustc_hir as hir;
use rustc_hir::def::Res;
use rustc_span::{Ident, Span, SyntaxContext};

use super::input::Probe;
use super::wire as w;
use crate::PerOwnerLoweringState;

struct Capture<'a>(&'a Probe);

impl Capture<'_> {
    fn span(&self, span: Span) -> Option<w::SourceSpan> {
        if span.ctxt() != SyntaxContext::root() || span.parent() != Some(self.0.current_owner) {
            return None;
        }
        if span.is_dummy() { return Some(w::SourceSpan::Dummy); }
        let base = self.0.current_span;
        if span.lo() < base.lo() || span.hi() > base.hi() { return None; }
        Some(w::SourceSpan::Relative {
            lo: (span.lo() - base.lo()).0, hi: (span.hi() - base.lo()).0,
        })
    }
    fn id(&self, id: hir::HirId) -> Option<u32> {
        (id.owner.def_id == self.0.current_owner).then_some(id.local_id.as_u32())
    }
    fn node(&self, id: hir::HirId, span: Span) -> Option<w::Node> {
        Some(w::Node { local: self.id(id)?, span: self.span(span)? })
    }
    fn ident(&self, ident: Ident) -> Option<w::Ident> {
        Some(w::Ident { text: ident.name.as_str().to_owned(), span: self.span(ident.span)? })
    }
    fn res(&self, res: Res, segment: bool) -> Option<w::Resolution> {
        Some(match res {
            Res::PrimTy(ty) if !matches!(ty, hir::PrimTy::Str) =>
                w::Resolution::Primitive(ty.name_str().to_owned()),
            Res::Local(id) => w::Resolution::Local(self.id(id)?),
            Res::Err if segment => w::Resolution::MissingSegment,
            _ => return None,
        })
    }
    fn path(&self, qpath: &hir::QPath<'_>) -> Option<w::Path> {
        let hir::QPath::Resolved(None, path) = qpath else { return None; };
        let [segment] = path.segments else { return None; };
        if segment.args.is_some() || segment.delegation_child_segment { return None; }
        Some(w::Path { span: self.span(path.span)?, resolution: self.res(path.res, false)?,
            segment_local: self.id(segment.hir_id)?, segment_ident: self.ident(segment.ident)?,
            segment_resolution: self.res(segment.res, true)?, infer_args: segment.infer_args })
    }
    fn ty(&self, ty: &hir::Ty<'_>) -> Option<w::Ty> {
        let hir::TyKind::Path(path) = &ty.kind else { return None; };
        Some(w::Ty { node: self.node(ty.hir_id, ty.span)?, path: self.path(path)? })
    }
    fn pat(&self, pat: &hir::Pat<'_>) -> Option<w::Pattern> {
        if !pat.default_binding_modes { return None; }
        let kind = match pat.kind {
            hir::PatKind::Wild => w::PatternKind::Wild,
            hir::PatKind::Binding(mode, id, ident, None) if mode == hir::BindingMode::NONE =>
                w::PatternKind::Binding { binding_local: self.id(id)?, ident: self.ident(ident)? },
            _ => return None,
        };
        Some(w::Pattern { node: self.node(pat.hir_id, pat.span)?, kind })
    }
    fn literal(&self, value: ast::LitKind) -> Option<w::Literal> {
        Some(match value {
            ast::LitKind::Bool(value) => w::Literal::Bool(value),
            ast::LitKind::Byte(value) => w::Literal::Byte(value),
            ast::LitKind::Char(value) => w::Literal::Char(value),
            ast::LitKind::Int(value, ty) => w::Literal::Int(value.to_string(), match ty {
                ast::LitIntType::Unsuffixed => None,
                ast::LitIntType::Signed(ty) => Some(hir::PrimTy::Int(ty).name_str().to_owned()),
                ast::LitIntType::Unsigned(ty) => Some(hir::PrimTy::Uint(ty).name_str().to_owned()),
            }),
            ast::LitKind::Float(value, ty) => w::Literal::Float(value.as_str().to_owned(), match ty {
                ast::LitFloatType::Unsuffixed => None,
                ast::LitFloatType::Suffixed(ty) => Some(hir::PrimTy::Float(ty).name_str().to_owned()),
            }),
            _ => return None,
        })
    }
    fn expr(&self, expr: &hir::Expr<'_>, depth: usize) -> Option<w::Expr> {
        if depth >= 64 { return None; }
        let kind = match &expr.kind {
            hir::ExprKind::Lit(lit) => w::ExprKind::Literal(self.span(lit.span)?, self.literal(lit.node)?),
            hir::ExprKind::Path(path) => w::ExprKind::LocalPath(self.path(path)?),
            hir::ExprKind::Tup(values) if values.is_empty() => w::ExprKind::Unit,
            hir::ExprKind::Unary(op, value) => w::ExprKind::Unary(match op {
                hir::UnOp::Not => w::Unary::Not,
                hir::UnOp::Neg => w::Unary::Neg,
                _ => return None,
            }, Box::new(self.expr(value, depth + 1)?)),
            hir::ExprKind::Binary(op, left, right) => w::ExprKind::Binary(op.node.as_str().to_owned(),
                self.span(op.span)?, Box::new(self.expr(left, depth + 1)?), Box::new(self.expr(right, depth + 1)?)),
            hir::ExprKind::Block(block, None) => w::ExprKind::Block(self.block(block, depth + 1)?),
            hir::ExprKind::Ret(value) => w::ExprKind::Return(match value {
                Some(value) => Some(Box::new(self.expr(value, depth + 1)?)), None => None,
            }),
            _ => return None,
        };
        Some(w::Expr { node: self.node(expr.hir_id, expr.span)?, kind })
    }
    fn block(&self, block: &hir::Block<'_>, depth: usize) -> Option<w::Block> {
        if depth >= 64 || block.targeted_by_break || !matches!(block.rules, hir::BlockCheckMode::DefaultBlock)
            || block.stmts.len() > 512 { return None; }
        let statements = block.stmts.iter().map(|stmt| {
            let kind = match stmt.kind {
                hir::StmtKind::Let(local) => {
                    if local.super_.is_some() || local.els.is_some() || !matches!(local.source, hir::LocalSource::Normal) {
                        return None;
                    }
                    w::StatementKind::Let { node: self.node(local.hir_id, local.span)?, pat: self.pat(local.pat)?,
                        ty: match local.ty { Some(ty) => Some(self.ty(ty)?), None => None },
                        init: match local.init { Some(expr) => Some(self.expr(expr, depth + 1)?), None => None } }
                }
                hir::StmtKind::Expr(expr) => w::StatementKind::Expr(self.expr(expr, depth + 1)?),
                hir::StmtKind::Semi(expr) => w::StatementKind::Semi(self.expr(expr, depth + 1)?),
                _ => return None,
            };
            Some(w::Statement { node: self.node(stmt.hir_id, stmt.span)?, kind })
        }).collect::<Option<Vec<_>>>()?;
        Some(w::Block { node: self.node(block.hir_id, block.span)?, statements,
            tail: match block.expr { Some(expr) => Some(Box::new(self.expr(expr, depth + 1)?)), None => None } })
    }
}

pub(super) fn capture(probe: &Probe, state: &PerOwnerLoweringState<'_, '_>, node: hir::OwnerNode<'_>) -> Option<w::OwnerTree> {
    let hir::OwnerNode::Item(item) = node else { return None; };
    let hir::ItemKind::Fn { ident, sig, generics, body, has_body: true } = &item.kind else { return None; };
    if item.owner_id.def_id != probe.current_owner || item.eii.is_some()
        || !matches!(sig.header.safety, hir::HeaderSafety::Normal(hir::Safety::Safe))
        || !matches!(sig.header.constness, hir::Constness::NotConst)
        || !matches!(sig.header.asyncness, hir::IsAsync::NotAsync) || sig.header.abi != ExternAbi::Rust
        || !generics.params.is_empty() || !generics.predicates.is_empty() || generics.has_where_clause_predicates
        || !matches!(sig.decl.implicit_self(), hir::ImplicitSelfKind::None)
        || sig.decl.c_variadic() || sig.decl.splatted().is_some() { return None; }
    let [(_, value)] = state.bodies.as_slice() else { return None; };
    if value.id() != *body { return None; }
    let c = Capture(probe);
    Some(w::OwnerTree {
        ident: c.ident(*ident)?, span: c.span(item.span)?, vis_span: c.span(item.vis_span)?,
        signature_span: c.span(sig.span)?, generics_span: c.span(generics.span)?,
        where_span: c.span(generics.where_clause_span)?,
        lifetime_elision_allowed: sig.decl.lifetime_elision_allowed(),
        input_types: sig.decl.inputs.iter().map(|ty| c.ty(ty)).collect::<Option<Vec<_>>>()?,
        output_type: match sig.decl.output {
            hir::FnRetTy::DefaultReturn(span) => w::ReturnType::Default(c.span(span)?),
            hir::FnRetTy::Return(ty) => w::ReturnType::Primitive(c.ty(ty)?),
        },
        params: value.params.iter().map(|param| Some(w::Param { node: c.node(param.hir_id, param.span)?,
            ty_span: c.span(param.ty_span)?, pat: c.pat(param.pat)? })).collect::<Option<Vec<_>>>()?,
        value: c.expr(value.value, 0)?, local_id_limit: state.item_local_id_counter.as_u32(),
    })
}
