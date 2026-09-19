//! Cold actual HIR -> closed wire. Exhaustive struct patterns deliberately
//! require an explicit decision if the pinned HIR gains another field.
use rustc_ast as ast;
use rustc_hir::{self as hir, def::Res};
use rustc_span::{Ident, Span, SyntaxContext};
use super::{Candidate, validate::{self, Current}, wire as w};

struct Capture<'a, 'b> { candidate: &'a Candidate, current: &'a Current<'b> }
impl Capture<'_, '_> {
    fn span(&self, span: Span) -> Option<w::SourceSpan> {
        if span.ctxt() != SyntaxContext::root() || span.parent() != Some(self.candidate.owner.def_id) {
            return None;
        }
        let result = if span.is_dummy() { w::SourceSpan::Dummy } else {
            let base = self.candidate.current_span;
            if span.lo() < base.lo() || span.hi() > base.hi() { return None; }
            w::SourceSpan::Relative { lo: (span.lo() - base.lo()).0, hi: (span.hi() - base.lo()).0 }
        };
        validate::span(&result, self.current.source)?; Some(result)
    }
    fn id(&self, id: hir::HirId) -> Option<u32> {
        let local = id.local_id.as_u32();
        if id.owner != self.current.owner || local < self.current.start || local >= self.current.journal.end {
            return None;
        }
        Some(local - self.current.start)
    }
    fn node(&self, id: hir::HirId, span: Span) -> Option<w::Node> {
        Some(w::Node { relative: self.id(id)?, span: self.span(span)? })
    }
    fn ident(&self, ident: Ident) -> Option<w::Ident> {
        Some(w::Ident { text: ident.name.as_str().to_owned(), span: self.span(ident.span)? })
    }
    fn local(&self, id: hir::HirId) -> Option<w::LocalRef> {
        self.current.locals.iter().find_map(|(reference, current)| (*current == id).then(|| reference.clone()))
    }
    fn resolution(&self, res: Res, relative: u32, segment: bool) -> Option<w::Resolution> {
        let ordinal = self.current.origin(relative)?;
        let (expected, reference) = self.current.resolution(ordinal, segment)?;
        (res == expected).then_some(reference)
    }
    fn segment(&self, segment: &hir::PathSegment<'_>) -> Option<w::Segment> {
        let hir::PathSegment { ident, hir_id, res, args, infer_args, delegation_child_segment } = *segment;
        if args.is_some() || delegation_child_segment { return None; }
        let relative = self.id(hir_id)?;
        Some(w::Segment { relative, ident: self.ident(ident)?, resolution: self.resolution(res, relative, true)?, infer_args })
    }
    fn path(&self, path: &hir::QPath<'_>, relative: u32) -> Option<w::Path> {
        let hir::QPath::Resolved(None, path) = path else { return None; };
        let hir::Path { span, res, segments } = **path;
        if segments.is_empty() { return None; }
        Some(w::Path { span: self.span(span)?, resolution: self.resolution(res, relative, false)?,
            segments: segments.iter().map(|s| self.segment(s)).collect::<Option<_>>()? })
    }
    fn pattern(&self, pattern: &hir::Pat<'_>) -> Option<w::Pattern> {
        let hir::Pat { hir_id, kind, span, default_binding_modes } = *pattern;
        if !default_binding_modes { return None; }
        let kind = match kind {
            hir::PatKind::Wild => w::PatternKind::Wild,
            hir::PatKind::Binding(mode, target, ident, None) => w::PatternKind::Binding {
                mode: binding_mode(mode), target: self.local(target)?, ident: self.ident(ident)? },
            _ => return None,
        };
        Some(w::Pattern { node: self.node(hir_id, span)?, kind, default_binding_modes })
    }
    fn exprs(&self, values: &[hir::Expr<'_>], depth: usize) -> Option<Vec<w::Expr>> {
        values.iter().map(|e| self.expr(e, depth)).collect()
    }
    fn expr(&self, expr: &hir::Expr<'_>, depth: usize) -> Option<w::Expr> {
        if depth >= 64 { return None; }
        let hir::Expr { hir_id, kind, span } = *expr;
        let node = self.node(hir_id, span)?;
        use hir::ExprKind as H; use w::ExprKind as W;
        let kind = match kind {
            H::Array(values) => W::Array(self.exprs(values, depth + 1)?),
            H::Tup(values) => W::Tuple(self.exprs(values, depth + 1)?),
            H::Lit(lit) => W::Literal { span: self.span(lit.span)?, value: literal(lit.node)? },
            H::Path(path) => W::Path(self.path(&path, node.relative)?),
            H::Call(function, arguments) => W::Call { function: Box::new(self.expr(function, depth + 1)?),
                arguments: self.exprs(arguments, depth + 1)? },
            H::MethodCall(segment, receiver, arguments, span) => W::Method { segment: self.segment(segment)?,
                receiver: Box::new(self.expr(receiver, depth + 1)?), arguments: self.exprs(arguments, depth + 1)?, span: self.span(span)? },
            H::Unary(op, value) => W::Unary(match op {
                hir::UnOp::Not => w::Unary::Not, hir::UnOp::Neg => w::Unary::Negate,
                hir::UnOp::Deref => w::Unary::Dereference,
            }, Box::new(self.expr(value, depth + 1)?)),
            H::Binary(op, left, right) => W::Binary { operation: op.node.as_str().to_owned(), span: self.span(op.span)?,
                left: Box::new(self.expr(left, depth + 1)?), right: Box::new(self.expr(right, depth + 1)?) },
            H::Block(block, None) => W::Block(self.block(block, depth + 1)?),
            H::If(condition, then, otherwise) => W::If { condition: Box::new(self.expr(condition, depth + 1)?),
                then: Box::new(self.expr(then, depth + 1)?),
                otherwise: otherwise.map(|e| self.expr(e, depth + 1).map(Box::new)).transpose_option()? },
            H::Assign(left, right, span) => W::Assign { left: Box::new(self.expr(left, depth + 1)?),
                right: Box::new(self.expr(right, depth + 1)?), span: self.span(span)? },
            H::AssignOp(op, left, right) => W::AssignOp { operation: op.node.as_str().to_owned(), span: self.span(op.span)?,
                left: Box::new(self.expr(left, depth + 1)?), right: Box::new(self.expr(right, depth + 1)?) },
            H::Field(value, ident) => W::Field(Box::new(self.expr(value, depth + 1)?), self.ident(ident)?),
            H::Index(value, index, span) => W::Index { value: Box::new(self.expr(value, depth + 1)?),
                index: Box::new(self.expr(index, depth + 1)?), span: self.span(span)? },
            H::AddrOf(kind, mutable, value) => W::Borrow { kind: match kind {
                hir::BorrowKind::Ref => w::Borrow::Reference, hir::BorrowKind::Raw => w::Borrow::Raw,
                _ => return None,
            }, mutability: mutability(mutable), value: Box::new(self.expr(value, depth + 1)?) },
            H::Ret(value) => W::Return(value.map(|e| self.expr(e, depth + 1).map(Box::new)).transpose_option()?),
            _ => return None,
        };
        Some(w::Expr { node, kind })
    }
    fn block(&self, block: &hir::Block<'_>, depth: usize) -> Option<w::Block> {
        if depth >= 64 { return None; }
        let hir::Block { stmts, expr, hir_id, rules, span, targeted_by_break } = *block;
        if targeted_by_break { return None; }
        let rules = match rules {
            hir::BlockCheckMode::DefaultBlock => w::BlockRules::Default,
            hir::BlockCheckMode::UnsafeBlock(hir::UnsafeSource::UserProvided) => w::BlockRules::UnsafeUser,
            _ => return None,
        };
        Some(w::Block { node: self.node(hir_id, span)?, rules, targeted_by_break,
            statements: stmts.iter().map(|s| self.statement(s, depth + 1)).collect::<Option<_>>()?,
            tail: expr.map(|e| self.expr(e, depth + 1).map(Box::new)).transpose_option()? })
    }
    fn statement(&self, statement: &hir::Stmt<'_>, depth: usize) -> Option<w::Statement> {
        let hir::Stmt { hir_id, kind, span } = *statement;
        let kind = match kind {
            hir::StmtKind::Let(local) => {
                let hir::LetStmt { super_, pat, ty, init, els, hir_id, span, source } = *local;
                if super_.is_some() || ty.is_some() || els.is_some() || !matches!(source, hir::LocalSource::Normal) {
                    return None;
                }
                w::StatementKind::Let(w::Local { node: self.node(hir_id, span)?, pattern: self.pattern(pat)?,
                    init: init.map(|e| self.expr(e, depth + 1)).transpose_option()? })
            }
            hir::StmtKind::Expr(value) => w::StatementKind::Expr(self.expr(value, depth + 1)?),
            hir::StmtKind::Semi(value) => w::StatementKind::Semi(self.expr(value, depth + 1)?),
            _ => return None,
        };
        Some(w::Statement { node: self.node(hir_id, span)?, kind })
    }
}
// Unlike flatten(), preserve failure of a present unsupported child.
trait TransposeOption<T> { fn transpose_option(self) -> Option<Option<T>>; }
impl<T> TransposeOption<T> for Option<Option<T>> {
    fn transpose_option(self) -> Option<Option<T>> { match self { Some(v) => v.map(Some), None => Some(None) } }
}
fn mutability(value: hir::Mutability) -> w::Mutability {
    match value { hir::Mutability::Not => w::Mutability::Immutable, hir::Mutability::Mut => w::Mutability::Mutable }
}
fn binding_mode(value: hir::BindingMode) -> w::BindingMode {
    let hir::BindingMode(by_ref, mutable) = value;
    w::BindingMode { mutability: mutability(mutable), by_ref: match by_ref {
        hir::ByRef::No => w::ByRef::No,
        hir::ByRef::Yes(pinned, mutable) => w::ByRef::Yes {
            pinned: matches!(pinned, hir::Pinnedness::Pinned), mutability: mutability(mutable) },
    } }
}
fn style(value: ast::StrStyle) -> w::StringStyle {
    match value { ast::StrStyle::Cooked => w::StringStyle::Cooked, ast::StrStyle::Raw(n) => w::StringStyle::Raw(n) }
}
fn literal(value: ast::LitKind) -> Option<w::Literal> {
    Some(match value {
        ast::LitKind::Str(s, ty) => w::Literal::String(s.as_str().to_owned(), style(ty)),
        ast::LitKind::ByteStr(s, ty) => w::Literal::Bytes(s.as_byte_str().to_vec(), style(ty)),
        ast::LitKind::CStr(s, ty) => w::Literal::CString(s.as_byte_str().to_vec(), style(ty)),
        ast::LitKind::Bool(v) => w::Literal::Bool(v), ast::LitKind::Byte(v) => w::Literal::Byte(v),
        ast::LitKind::Char(v) => w::Literal::Char(v),
        ast::LitKind::Int(v, ty) => w::Literal::Integer(v.to_string(), match ty {
            ast::LitIntType::Unsuffixed => None,
            ast::LitIntType::Signed(t) => Some(hir::PrimTy::Int(t).name_str().to_owned()),
            ast::LitIntType::Unsigned(t) => Some(hir::PrimTy::Uint(t).name_str().to_owned()),
        }),
        ast::LitKind::Float(v, ty) => w::Literal::Float(v.as_str().to_owned(), match ty {
            ast::LitFloatType::Unsuffixed => None,
            ast::LitFloatType::Suffixed(t) => Some(hir::PrimTy::Float(t).name_str().to_owned()),
        }),
        ast::LitKind::Err(_) => return None,
    })
}

pub(super) fn capture(candidate: &Candidate, current: &Current<'_>, value: &hir::Expr<'_>) -> Option<w::BodyTree> {
    Some(w::BodyTree { value: Capture { candidate, current }.expr(value, 0)? })
}
