//! Owned, typed values for a checked current-session body. This module performs
//! no HIR allocation, symbol/span interning, query or LoweringContext mutation.
//! Its opaque result is NOT a ReadyHit: no exclusive context, vacancy/effect
//! preflight or hit commit exists. The separate private child audits cold
//! materialization only after stock lowering, which always supplies the result.
use std::collections::BTreeMap;
use rustc_ast as ast;
use rustc_hir::{self as hir, def::Res};
use rustc_span::BytePos;
use super::{validate::{self, CheckedTree, Current}, wire as w};
#[path = "prepared_audit.rs"]
mod cold;

/// No public fields, deserializer, unchecked constructor or hit materializer.
/// Immutable borrowing binds this token to the exact Current until consumed;
/// it does not grant exclusive access to the LoweringContext.
pub(super) struct PreparedBody<'current, 'input> {
    current: &'current Current<'input>,
    expected: w::BodyTree,
    owner: hir::OwnerId,
    start: u32,
    end: u32, // Exclusive; may equal ItemLocalId::INVALID, never a node ID.
    source_start: BytePos,
    source_end: BytePos,
    source: String,
    prefix: BTreeMap<u32, hir::HirId>,
    value: Expr,
}

/// Coordinates are absolute in this current SourceMap, UTF-8 checked against
/// the exact current owner source. A future exclusive commit must use current
/// root hygiene and the ordinary lower_span parent policy, including Dummy.
/// Constructing this recipe does not construct or intern a rustc Span.
enum SpanRecipe { Dummy, Current { owner: hir::OwnerId, lo: BytePos, hi: BytePos } }
struct Node { id: hir::HirId, span: SpanRecipe }
struct Ident { text: String, span: SpanRecipe }
struct Segment { id: hir::HirId, ident: Ident, resolution: Res, infer_args: bool }
struct Path { span: SpanRecipe, resolution: Res, segments: Vec<Segment> }
enum PatternKind { Wild, Binding { mode: hir::BindingMode, target: hir::HirId, ident: Ident } }
struct Pattern { node: Node, kind: PatternKind, default_binding_modes: bool }
enum Literal {
    String(String, ast::StrStyle), Bytes(Vec<u8>, ast::StrStyle), CString(Vec<u8>, ast::StrStyle),
    Bool(bool), Byte(u8), Char(char), Integer(u128, ast::LitIntType), Float(String, ast::LitFloatType),
}
enum ExprKind {
    Array(Vec<Expr>), Tuple(Vec<Expr>), Literal { span: SpanRecipe, value: Literal }, Path(Path),
    Call { function: Box<Expr>, arguments: Vec<Expr> },
    Method { segment: Segment, receiver: Box<Expr>, arguments: Vec<Expr>, span: SpanRecipe },
    Unary(hir::UnOp, Box<Expr>),
    Binary { operation: hir::BinOpKind, span: SpanRecipe, left: Box<Expr>, right: Box<Expr> },
    Block(Block), If { condition: Box<Expr>, then: Box<Expr>, otherwise: Option<Box<Expr>> },
    Assign { left: Box<Expr>, right: Box<Expr>, span: SpanRecipe },
    AssignOp { operation: hir::AssignOpKind, span: SpanRecipe, left: Box<Expr>, right: Box<Expr> },
    Field(Box<Expr>, Ident), Index { value: Box<Expr>, index: Box<Expr>, span: SpanRecipe },
    Borrow { kind: hir::BorrowKind, mutability: hir::Mutability, value: Box<Expr> },
    Return(Option<Box<Expr>>),
}
struct Expr { node: Node, kind: ExprKind }
struct Local { node: Node, pattern: Pattern, init: Option<Expr> }
enum StatementKind { Let(Local), Expr(Expr), Semi(Expr) }
struct Statement { node: Node, kind: StatementKind }
struct Block {
    node: Node, statements: Vec<Statement>, tail: Option<Box<Expr>>,
    rules: hir::BlockCheckMode, targeted_by_break: bool,
}

/// Repeat full tree/reference/order validation with THIS Current. A CheckedTree
/// produced against another Current is not a transferable proof. Valid trees
/// may rebase to new IDs/coordinates; only these newly checked values survive.
pub(super) fn prepare<'current, 'input>(tree: &CheckedTree,
    current: &'current Current<'input>) -> Option<PreparedBody<'current, 'input>> {
    let prefix = current_state(current)?;
    let checked = validate::check(tree.tree().clone(), current)?;
    let value = Convert { current }.expr(&checked.tree().value)?;
    Some(PreparedBody { current, expected: checked.tree().clone(),
        owner: current.owner, start: current.start, end: current.journal.end,
        source_start: BytePos(current.source_start), source_end: BytePos(current.source_end),
        source: current.source.to_owned(), prefix, value })
}

/// Cold-only API: returns no HIR and offers no materialization/commit shortcut.
/// The caller has already run stock lowering and checked the exact exit frame.
pub(super) fn audit(lctx: &crate::LoweringContext<'_, '_>, candidate: &super::Candidate,
    expected: &CheckedTree, prepared: PreparedBody<'_, '_>) -> Option<()> {
    cold::audit(lctx, candidate, expected, prepared)
}

fn current_state(current: &Current<'_>) -> Option<BTreeMap<u32, hir::HirId>> {
    let invalid = hir::ItemLocalId::INVALID.as_u32();
    if current.start == 0 || current.start >= invalid || current.start != current.journal.start
        || current.start.checked_add(current.journal.journal().end_delta)? != current.journal.end
        || current.journal.end > invalid || !current.source_context.is_root()
        || current.source_start.checked_add(u32::try_from(current.source.len()).ok()?)? != current.source_end
        || current.resolutions.len() != current.kinds.len()
        || current.references.len() != current.kinds.len() { return None; }
    let mut prefix = BTreeMap::new(); let mut locals = BTreeMap::new();
    for (&ordinal, &local) in &current.journal.prefix_bindings {
        if local == 0 || local >= current.start { return None; }
        let id = hir::HirId { owner: current.owner, local_id: hir::ItemLocalId::from_u32(local) };
        prefix.insert(ordinal, id); locals.insert(w::LocalRef::Parameter(ordinal), id);
    }
    for &relative in current.journal.bindings.values() {
        let id = current_id(current, relative)?;
        locals.insert(w::LocalRef::Body(relative), id);
    }
    // Compare the complete map, including unused parameter bindings. Names do
    // not recover bindings, and a foreign owner or stale prefix is rejected.
    if locals != current.locals { return None; }
    for (ordinal, (res, reference)) in current.resolutions.iter().zip(&current.references).enumerate() {
        match (res, reference) {
            (None, None) | (Some(Res::Err), Some(w::Resolution::MissingSegment)) => (),
            (Some(Res::Local(id)), Some(w::Resolution::Local(reference)))
                if current.locals.get(reference) == Some(id) => (),
            (Some(res), Some(w::Resolution::Input(index)))
                if !matches!(res, Res::Local(_) | Res::Err) && *index as usize == ordinal => (),
            _ => return None,
        }
    }
    Some(prefix)
}

fn current_id(current: &Current<'_>, relative: u32) -> Option<hir::HirId> {
    let local = current.start.checked_add(relative)?;
    if relative >= current.journal.journal().end_delta || local >= current.journal.end
        || local >= hir::ItemLocalId::INVALID.as_u32() { return None; }
    Some(hir::HirId { owner: current.owner, local_id: hir::ItemLocalId::from_u32(local) })
}
fn span(value: &w::SourceSpan, current: &Current<'_>) -> Option<SpanRecipe> {
    validate::span(value, current.source)?;
    match *value {
        w::SourceSpan::Dummy => Some(SpanRecipe::Dummy),
        w::SourceSpan::Relative { lo, hi } => {
            let lo = current.source_start.checked_add(lo)?;
            let hi = current.source_start.checked_add(hi)?;
            if lo > hi || hi > current.source_end { return None; }
            Some(SpanRecipe::Current { owner: current.owner, lo: BytePos(lo), hi: BytePos(hi) })
        }
    }
}

struct Convert<'a, 'b> { current: &'a Current<'b> }
impl Convert<'_, '_> {
    fn node(&self, value: &w::Node) -> Option<Node> {
        let w::Node { relative, span: s } = value;
        Some(Node { id: current_id(self.current, *relative)?, span: span(s, self.current)? })
    }
    fn ident(&self, value: &w::Ident) -> Option<Ident> {
        let w::Ident { text, span: s } = value;
        Some(Ident { text: text.clone(), span: span(s, self.current)? })
    }
    fn resolution(&self, value: &w::Resolution, relative: u32, segment: bool) -> Option<Res> {
        let ordinal = self.current.origin(relative)?;
        let (res, expected) = self.current.resolution(ordinal, segment)?;
        (*value == expected).then_some(res)
    }
    fn segment(&self, value: &w::Segment) -> Option<Segment> {
        let w::Segment { relative, ident, resolution, infer_args } = value;
        Some(Segment { id: current_id(self.current, *relative)?, ident: self.ident(ident)?,
            resolution: self.resolution(resolution, *relative, true)?, infer_args: *infer_args })
    }
    fn pattern(&self, value: &w::Pattern) -> Option<Pattern> {
        let w::Pattern { node, kind, default_binding_modes } = value;
        let kind = match kind {
            w::PatternKind::Wild => PatternKind::Wild,
            w::PatternKind::Binding { mode, target, ident } => PatternKind::Binding {
                mode: binding_mode(*mode), target: *self.current.locals.get(target)?, ident: self.ident(ident)? },
        };
        Some(Pattern { node: self.node(node)?, kind, default_binding_modes: *default_binding_modes })
    }
    fn exprs(&self, values: &[w::Expr]) -> Option<Vec<Expr>> { values.iter().map(|v| self.expr(v)).collect() }
    fn boxed(&self, value: &w::Expr) -> Option<Box<Expr>> { self.expr(value).map(Box::new) }
    fn optional(&self, value: &Option<Box<w::Expr>>) -> Option<Option<Box<Expr>>> {
        match value { None => Some(None), Some(value) => Some(Some(self.boxed(value)?)) }
    }
    fn expr(&self, value: &w::Expr) -> Option<Expr> {
        use w::ExprKind as W; use ExprKind as E;
        let w::Expr { node, kind } = value;
        let kind = match kind {
            W::Array(values) => E::Array(self.exprs(values)?),
            W::Tuple(values) => E::Tuple(self.exprs(values)?),
            W::Literal { span: s, value } => E::Literal { span: span(s, self.current)?, value: literal(value)? },
            W::Path(w::Path { span: s, resolution, segments }) => E::Path(Path {
                span: span(s, self.current)?, resolution: self.resolution(resolution, node.relative, false)?,
                segments: segments.iter().map(|v| self.segment(v)).collect::<Option<_>>()? }),
            W::Call { function, arguments } => E::Call { function: self.boxed(function)?, arguments: self.exprs(arguments)? },
            W::Method { segment, receiver, arguments, span: s } => E::Method { segment: self.segment(segment)?,
                receiver: self.boxed(receiver)?, arguments: self.exprs(arguments)?, span: span(s, self.current)? },
            W::Unary(operation, value) => E::Unary(match operation {
                w::Unary::Not => hir::UnOp::Not, w::Unary::Negate => hir::UnOp::Neg,
                w::Unary::Dereference => hir::UnOp::Deref }, self.boxed(value)?),
            W::Binary { operation, span: s, left, right } => E::Binary { operation: binary(operation)?,
                span: span(s, self.current)?, left: self.boxed(left)?, right: self.boxed(right)? },
            W::Block(block) => E::Block(self.block(block)?),
            W::If { condition, then, otherwise } => E::If { condition: self.boxed(condition)?,
                then: self.boxed(then)?, otherwise: self.optional(otherwise)? },
            W::Assign { left, right, span: s } => E::Assign { left: self.boxed(left)?,
                right: self.boxed(right)?, span: span(s, self.current)? },
            W::AssignOp { operation, span: s, left, right } => E::AssignOp { operation: assignment(operation)?,
                span: span(s, self.current)?, left: self.boxed(left)?, right: self.boxed(right)? },
            W::Field(value, ident) => E::Field(self.boxed(value)?, self.ident(ident)?),
            W::Index { value, index, span: s } => E::Index { value: self.boxed(value)?,
                index: self.boxed(index)?, span: span(s, self.current)? },
            W::Borrow { kind, mutability: m, value } => E::Borrow { kind: match kind {
                w::Borrow::Reference => hir::BorrowKind::Ref, w::Borrow::Raw => hir::BorrowKind::Raw },
                mutability: mutability(*m), value: self.boxed(value)? },
            W::Return(value) => E::Return(self.optional(value)?),
        };
        Some(Expr { node: self.node(node)?, kind })
    }
    fn statement(&self, value: &w::Statement) -> Option<Statement> {
        let w::Statement { node, kind } = value;
        let kind = match kind {
            w::StatementKind::Expr(v) => StatementKind::Expr(self.expr(v)?),
            w::StatementKind::Semi(v) => StatementKind::Semi(self.expr(v)?),
            w::StatementKind::Let(w::Local { node, pattern, init }) => StatementKind::Let(Local {
                node: self.node(node)?, pattern: self.pattern(pattern)?,
                init: match init { None => None, Some(v) => Some(self.expr(v)?) } }),
        };
        Some(Statement { node: self.node(node)?, kind })
    }
    fn block(&self, value: &w::Block) -> Option<Block> {
        let w::Block { node, statements, tail, rules, targeted_by_break } = value;
        Some(Block { node: self.node(node)?, statements: statements.iter().map(|v| self.statement(v)).collect::<Option<_>>()?,
            tail: self.optional(tail)?, rules: match rules {
                w::BlockRules::Default => hir::BlockCheckMode::DefaultBlock,
                w::BlockRules::UnsafeUser => hir::BlockCheckMode::UnsafeBlock(hir::UnsafeSource::UserProvided) },
            targeted_by_break: *targeted_by_break })
    }
}

fn mutability(value: w::Mutability) -> hir::Mutability {
    match value { w::Mutability::Immutable => hir::Mutability::Not, w::Mutability::Mutable => hir::Mutability::Mut }
}
fn binding_mode(value: w::BindingMode) -> hir::BindingMode {
    let w::BindingMode { by_ref, mutability: binding_mutability } = value;
    hir::BindingMode(match by_ref {
        w::ByRef::No => hir::ByRef::No,
        w::ByRef::Yes { pinned, mutability: m } => hir::ByRef::Yes(
            if pinned { hir::Pinnedness::Pinned } else { hir::Pinnedness::Not }, mutability(m)),
    }, mutability(binding_mutability))
}
fn style(value: w::StringStyle) -> ast::StrStyle {
    match value { w::StringStyle::Cooked => ast::StrStyle::Cooked, w::StringStyle::Raw(n) => ast::StrStyle::Raw(n) }
}
fn integer_type(value: Option<&str>) -> Option<ast::LitIntType> {
    use ast::{IntTy as I, UintTy as U, LitIntType as T};
    Some(match value {
        None => T::Unsuffixed,
        Some("i8") => T::Signed(I::I8), Some("i16") => T::Signed(I::I16),
        Some("i32") => T::Signed(I::I32), Some("i64") => T::Signed(I::I64),
        Some("i128") => T::Signed(I::I128), Some("isize") => T::Signed(I::Isize),
        Some("u8") => T::Unsigned(U::U8), Some("u16") => T::Unsigned(U::U16),
        Some("u32") => T::Unsigned(U::U32), Some("u64") => T::Unsigned(U::U64),
        Some("u128") => T::Unsigned(U::U128), Some("usize") => T::Unsigned(U::Usize),
        Some(_) => return None,
    })
}
fn float_type(value: Option<&str>) -> Option<ast::LitFloatType> {
    use ast::{FloatTy as F, LitFloatType as T};
    Some(match value { None => T::Unsuffixed,
        Some("f16") => T::Suffixed(F::F16), Some("f32") => T::Suffixed(F::F32),
        Some("f64") => T::Suffixed(F::F64), Some("f128") => T::Suffixed(F::F128), Some(_) => return None })
}
fn literal(value: &w::Literal) -> Option<Literal> {
    use w::Literal as W; use Literal as L;
    Some(match value {
        W::String(v, s) => L::String(v.clone(), style(*s)),
        W::Bytes(v, s) => L::Bytes(v.clone(), style(*s)),
        W::CString(v, s) => L::CString(v.clone(), style(*s)),
        W::Bool(v) => L::Bool(*v), W::Byte(v) => L::Byte(*v), W::Char(v) => L::Char(*v),
        W::Integer(v, suffix) => L::Integer(v.parse().ok()?, integer_type(suffix.as_deref())?),
        // Exact validated spelling survives; no host-float rounding or suffix interning.
        W::Float(v, suffix) => L::Float(v.clone(), float_type(suffix.as_deref())?),
    })
}
fn binary(value: &str) -> Option<hir::BinOpKind> {
    use hir::BinOpKind::*;
    Some(match value { "+" => Add, "-" => Sub, "*" => Mul, "/" => Div, "%" => Rem,
        "&&" => And, "||" => Or, "^" => BitXor, "&" => BitAnd, "|" => BitOr,
        "<<" => Shl, ">>" => Shr, "==" => Eq, "!=" => Ne, "<" => Lt, "<=" => Le,
        ">" => Gt, ">=" => Ge, _ => return None })
}
fn assignment(value: &str) -> Option<hir::AssignOpKind> {
    use hir::AssignOpKind::*;
    Some(match value { "+=" => AddAssign, "-=" => SubAssign, "*=" => MulAssign,
        "/=" => DivAssign, "%=" => RemAssign, "^=" => BitXorAssign, "&=" => BitAndAssign,
        "|=" => BitOrAssign, "<<=" => ShlAssign, ">>=" => ShrAssign, _ => return None })
}

#[cfg(test)]
mod tests {
    use super::*;
    use validate::tests::{checked, current, tree};

    #[test]
    fn preparation_uses_current_ids_and_absolute_checked_utf8_coordinates() {
        let journal = checked(); let mut current = current(&journal);
        let checked = validate::check(tree(), &current).unwrap();
        current.source_start = 200; current.source_end = 204;
        let prepared = prepare(&checked, &current).unwrap();
        assert_eq!(prepared.value.node.id.local_id.as_u32(), 5);
        assert_eq!(prepared.value.node.id.owner, current.owner);
        let SpanRecipe::Current { owner, lo, hi } = prepared.value.node.span else { panic!() };
        assert_eq!(owner, current.owner); assert_eq!((lo.0, hi.0), (200, 202));
        assert!(span(&w::SourceSpan::Relative { lo: 2, hi: 4 }, &current).is_some());
        assert!(span(&w::SourceSpan::Relative { lo: 3, hi: 4 }, &current).is_none());
        assert!(span(&w::SourceSpan::Relative { lo: 4, hi: 4 }, &current).is_some());
        assert!(matches!(span(&w::SourceSpan::Dummy, &current), Some(SpanRecipe::Dummy)));
        current.source_start = u32::MAX - 4; current.source_end = u32::MAX;
        assert!(prepare(&checked, &current).is_some());
        current.source_start += 1; // Current owner extent itself would overflow.
        assert!(prepare(&checked, &current).is_none());
        assert!(span(&w::SourceSpan::Relative { lo: 2, hi: 4 }, &current).is_none());
        let invalid = hir::ItemLocalId::INVALID.as_u32();
        let nodes = vec![super::super::journal::Node { body: true, binding: false, traits: false }; 2];
        let boundary = super::super::journal::check(journal.journal().clone(), &super::super::journal::Entry {
            start: invalid - 3, nodes: &nodes, prefix_bindings: &BTreeMap::new() }).unwrap();
        let mut relocated = validate::tests::current(&boundary); relocated.start = boundary.start;
        let prepared = prepare(&checked, &relocated).unwrap();
        assert_eq!(prepared.value.node.id.local_id.as_u32(), invalid - 1);
        assert_eq!(prepared.end, invalid);
        assert!(current_id(&relocated, boundary.journal().end_delta).is_none());
    }

    #[test]
    fn checked_tree_is_revalidated_against_exact_current_without_unchecked_token() {
        let journal = checked(); let mut current = current(&journal);
        let checked = validate::check(tree(), &current).unwrap();
        assert!(prepare(&checked, &current).is_some());
        current.start += 1; assert!(prepare(&checked, &current).is_none()); current.start -= 1;
        current.source_end -= 1; assert!(prepare(&checked, &current).is_none()); current.source_end += 1;
        current.locals.insert(w::LocalRef::Parameter(9), hir::HirId {
            owner: current.owner, local_id: hir::ItemLocalId::from_u32(1) });
        assert!(prepare(&checked, &current).is_none()); current.locals.clear();
        current.kinds = &[super::super::kinds::Kind::Block,
            super::super::kinds::Kind::Expression(super::super::kinds::Expr::Tuple)];
        assert!(prepare(&checked, &current).is_none());
    }

    #[test]
    fn unused_prefix_bindings_still_require_exact_current_owner_and_resolution() {
        use super::super::journal;
        use super::super::kinds::{Kind, Expr as K};
        let mut nodes = vec![journal::Node { body: true, binding: false, traits: false }; 2];
        nodes.push(journal::Node { body: false, binding: true, traits: false });
        let journal = journal::check(checked().journal().clone(), &journal::Entry {
            start: 3, nodes: &nodes, prefix_bindings: &BTreeMap::from([(2, 1)]) }).unwrap();
        let mut current = current(&journal);
        current.kinds = &[Kind::Block, Kind::Expression(K::Literal), Kind::Pattern { binding: true }];
        let reference = w::LocalRef::Parameter(2);
        let id = hir::HirId { owner: current.owner, local_id: hir::ItemLocalId::from_u32(1) };
        current.locals.insert(reference.clone(), id);
        current.resolutions.push(Some(Res::Local(id)));
        current.references.push(Some(w::Resolution::Local(reference.clone())));
        let checked = validate::check(tree(), &current).unwrap();
        assert_eq!(prepare(&checked, &current).unwrap().prefix[&2], id);
        current.locals.get_mut(&reference).unwrap().owner = hir::OwnerId {
            def_id: rustc_span::def_id::LocalDefId { local_def_index: rustc_span::def_id::DefIndex::from_u32(1) } };
        assert!(prepare(&checked, &current).is_none());
        current.locals.insert(reference, id);
        current.resolutions[2] = Some(Res::Local(hir::HirId { owner: current.owner,
            local_id: hir::ItemLocalId::from_u32(2) }));
        assert!(prepare(&checked, &current).is_none());
    }

    #[test]
    fn typed_operators_suffixes_and_integer_boundaries_are_fallible() {
        for op in [hir::AssignOpKind::AddAssign, hir::AssignOpKind::SubAssign,
            hir::AssignOpKind::MulAssign, hir::AssignOpKind::DivAssign, hir::AssignOpKind::RemAssign,
            hir::AssignOpKind::BitXorAssign, hir::AssignOpKind::BitAndAssign, hir::AssignOpKind::BitOrAssign,
            hir::AssignOpKind::ShlAssign, hir::AssignOpKind::ShrAssign] {
            assert_eq!(assignment(op.as_str()), Some(op));
            assert!(binary(op.as_str()).is_none());
        }
        assert_eq!(binary("&&"), Some(hir::BinOpKind::And));
        assert!(assignment("+").is_none()); assert!(binary("bogus").is_none());
        for name in ["i8", "i16", "i32", "i64", "i128", "isize", "u8", "u16", "u32", "u64", "u128", "usize"] {
            match integer_type(Some(name)).unwrap() {
                ast::LitIntType::Signed(ty) => assert_eq!(ty.name_str(), name),
                ast::LitIntType::Unsigned(ty) => assert_eq!(ty.name_str(), name), _ => panic!(),
            }
        }
        for name in ["f16", "f32", "f64", "f128"] {
            let ast::LitFloatType::Suffixed(ty) = float_type(Some(name)).unwrap() else { panic!() };
            assert_eq!(ty.name_str(), name);
        }
        assert!(integer_type(Some("f32")).is_none()); assert!(float_type(Some("u32")).is_none());
        let maximum = w::Literal::Integer(u128::MAX.to_string(), Some("u128".into()));
        let Literal::Integer(value, ty) = literal(&maximum).unwrap() else { panic!() };
        assert_eq!(value, u128::MAX); assert_eq!(ty, ast::LitIntType::Unsigned(ast::UintTy::U128));
        assert!(literal(&w::Literal::Integer("340282366920938463463374607431768211456".into(), None)).is_none());
        let Literal::Float(value, ty) = literal(&w::Literal::Float("1e-9999".into(), None)).unwrap() else { panic!() };
        assert_eq!(value, "1e-9999"); assert_eq!(ty, ast::LitFloatType::Unsuffixed);
    }
}
