use rustc_abi::ExternAbi;
use rustc_ast as ast;
use rustc_hir as hir;
use rustc_hir::def::Res;
use rustc_span::{BytePos, Ident, Span, Symbol, SyntaxContext, DUMMY_SP, respan};

use super::input::Probe;
use super::validate::CheckedTree;
use super::wire as w;
use crate::LoweringContext;

struct Materialize<'a, 'hir> {
    probe: &'a Probe,
    arena: &'hir hir::Arena<'hir>,
}

impl<'hir> Materialize<'_, 'hir> {
    fn span(&self, span: &w::SourceSpan) -> Span {
        let span = match *span {
            w::SourceSpan::Dummy => DUMMY_SP,
            w::SourceSpan::Relative { lo, hi } => Span::new(
                self.probe.current_span.lo() + BytePos(lo), self.probe.current_span.lo() + BytePos(hi),
                SyntaxContext::root(), None),
        };
        span.with_parent(Some(self.probe.current_owner))
    }
    fn id(&self, local: u32) -> hir::HirId {
        hir::HirId { owner: hir::OwnerId { def_id: self.probe.current_owner },
            local_id: hir::ItemLocalId::from_u32(local) }
    }
    fn ident(&self, ident: &w::Ident) -> Ident {
        Ident::new(Symbol::intern(&ident.text), self.span(&ident.span))
    }
    fn res(&self, res: &w::Resolution) -> Res {
        match res {
            w::Resolution::Primitive(name) => Res::PrimTy(w::primitive(name).unwrap()),
            w::Resolution::Local(id) => Res::Local(self.id(*id)),
            w::Resolution::MissingSegment => Res::Err,
        }
    }
    fn path(&self, path: &w::Path) -> hir::QPath<'hir> {
        let segment = hir::PathSegment { ident: self.ident(&path.segment_ident),
            hir_id: self.id(path.segment_local), res: self.res(&path.segment_resolution),
            args: None, infer_args: path.infer_args, delegation_child_segment: false };
        hir::QPath::Resolved(None, self.arena.alloc(hir::Path {
            span: self.span(&path.span), res: self.res(&path.resolution),
            segments: self.arena.alloc_from_iter([segment]),
        }))
    }
    fn ty(&self, ty: &w::Ty) -> hir::Ty<'hir> {
        hir::Ty { hir_id: self.id(ty.node.local), span: self.span(&ty.node.span),
            kind: hir::TyKind::Path(self.path(&ty.path)) }
    }
    fn pat(&self, pat: &w::Pattern) -> &'hir hir::Pat<'hir> {
        self.arena.alloc(hir::Pat { hir_id: self.id(pat.node.local), span: self.span(&pat.node.span),
            default_binding_modes: true, kind: match &pat.kind {
                w::PatternKind::Wild => hir::PatKind::Wild,
                w::PatternKind::Binding { binding_local, ident } => hir::PatKind::Binding(
                    hir::BindingMode::NONE, self.id(*binding_local), self.ident(ident), None),
            } })
    }
    fn literal(&self, lit: &w::Literal) -> ast::LitKind {
        match lit {
            w::Literal::Bool(value) => ast::LitKind::Bool(*value),
            w::Literal::Byte(value) => ast::LitKind::Byte(*value),
            w::Literal::Char(value) => ast::LitKind::Char(*value),
            w::Literal::Int(value, kind) => ast::LitKind::Int(value.parse::<u128>().unwrap().into(),
                w::integer_type(kind).unwrap()),
            w::Literal::Float(value, kind) => ast::LitKind::Float(Symbol::intern(value), w::float_type(kind).unwrap()),
        }
    }
    fn expr(&self, expr: &w::Expr) -> hir::Expr<'hir> {
        let kind = match &expr.kind {
            w::ExprKind::Unit => hir::ExprKind::Tup(&[]),
            w::ExprKind::Literal(span, lit) => hir::ExprKind::Lit(respan(self.span(span), self.literal(lit))),
            w::ExprKind::LocalPath(path) => hir::ExprKind::Path(self.path(path)),
            w::ExprKind::Unary(op, value) => hir::ExprKind::Unary(match op {
                w::Unary::Not => hir::UnOp::Not, w::Unary::Neg => hir::UnOp::Neg,
            }, self.arena.alloc(self.expr(value))),
            w::ExprKind::Binary(op, span, left, right) => hir::ExprKind::Binary(
                respan(self.span(span), w::binary(op).unwrap()),
                self.arena.alloc(self.expr(left)), self.arena.alloc(self.expr(right))),
            w::ExprKind::Block(block) => hir::ExprKind::Block(self.block(block), None),
            w::ExprKind::Return(value) => hir::ExprKind::Ret(value.as_ref().map(|value| &*self.arena.alloc(self.expr(value)))),
        };
        hir::Expr { hir_id: self.id(expr.node.local), span: self.span(&expr.node.span), kind }
    }
    fn block(&self, block: &w::Block) -> &'hir hir::Block<'hir> {
        let stmts = self.arena.alloc_from_iter(block.statements.iter().map(|stmt| {
            let kind = match &stmt.kind {
                w::StatementKind::Let { node, pat, ty, init } => hir::StmtKind::Let(self.arena.alloc(hir::LetStmt {
                    hir_id: self.id(node.local), span: self.span(&node.span), super_: None,
                    pat: self.pat(pat), ty: ty.as_ref().map(|ty| &*self.arena.alloc(self.ty(ty))),
                    init: init.as_ref().map(|expr| &*self.arena.alloc(self.expr(expr))), els: None,
                    source: hir::LocalSource::Normal,
                })),
                w::StatementKind::Expr(expr) => hir::StmtKind::Expr(self.arena.alloc(self.expr(expr))),
                w::StatementKind::Semi(expr) => hir::StmtKind::Semi(self.arena.alloc(self.expr(expr))),
            };
            hir::Stmt { hir_id: self.id(stmt.node.local), span: self.span(&stmt.node.span), kind }
        }));
        self.arena.alloc(hir::Block { hir_id: self.id(block.node.local), span: self.span(&block.node.span),
            stmts, expr: block.tail.as_ref().map(|expr| &*self.arena.alloc(self.expr(expr))),
            rules: hir::BlockCheckMode::DefaultBlock, targeted_by_break: false })
    }
}

pub(super) fn materialize<'hir>(lctx: &mut LoweringContext<'_, 'hir>, probe: &Probe, checked: &CheckedTree) -> hir::OwnerNode<'hir> {
    let tree = checked.get();
    let m = Materialize { probe, arena: lctx.arena };
    let params = m.arena.alloc_from_iter(tree.params.iter().map(|param| hir::Param {
        hir_id: m.id(param.node.local), span: m.span(&param.node.span),
        ty_span: m.span(&param.ty_span), pat: m.pat(&param.pat),
    }));
    let body = &*m.arena.alloc(hir::Body { params, value: m.arena.alloc(m.expr(&tree.value)) });
    let body_id = body.id();
    let decl = m.arena.alloc(hir::FnDecl {
        inputs: m.arena.alloc_from_iter(tree.input_types.iter().map(|ty| m.ty(ty))),
        output: match &tree.output_type {
            w::ReturnType::Default(span) => hir::FnRetTy::DefaultReturn(m.span(span)),
            w::ReturnType::Primitive(ty) => hir::FnRetTy::Return(m.arena.alloc(m.ty(ty))),
        },
        fn_decl_kind: hir::FnDeclFlags::default().set_lifetime_elision_allowed(tree.lifetime_elision_allowed),
    });
    let item = m.arena.alloc(hir::Item {
        owner_id: hir::OwnerId { def_id: probe.current_owner }, span: m.span(&tree.span),
        vis_span: m.span(&tree.vis_span), eii: None,
        kind: hir::ItemKind::Fn { ident: m.ident(&tree.ident), body: body_id, has_body: true,
            generics: m.arena.alloc(hir::Generics { params: &[], predicates: &[], has_where_clause_predicates: false,
                span: m.span(&tree.generics_span), where_clause_span: m.span(&tree.where_span) }),
            sig: hir::FnSig { span: m.span(&tree.signature_span), decl, header: hir::FnHeader {
                safety: hir::HeaderSafety::Normal(hir::Safety::Safe), constness: hir::Constness::NotConst,
                asyncness: hir::IsAsync::NotAsync, abi: ExternAbi::Rust,
            } },
        },
    });
    lctx.curr_owner.item_local_id_counter = hir::ItemLocalId::from_u32(tree.local_id_limit);
    lctx.curr_owner.bodies.push((body_id.hir_id.local_id, body));
    hir::OwnerNode::Item(item)
}
