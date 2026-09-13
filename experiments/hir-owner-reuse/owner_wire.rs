//! Proposed closed wire type: no rustc arena pointers, raw IDs, Symbol or Span.
//! Source-only: conversion, bounded decoding, publication and lookup are NOT implemented.
//! This represents the admitted owner tree; stock into_owner_info rebuilds derived tables.

use rustc_ast::{BinOpKind, LitFloatType, LitIntType};
use rustc_hir::PrimTy;
use rustc_macros::{Decodable, Encodable};
use rustc_span::def_id::LocalDefId;
use rustc_span::{BytePos, Span, SyntaxContext, DUMMY_SP};

#[derive(Encodable, Decodable)]
pub(super) enum SourceSpan { Dummy, Relative { lo: u32, hi: u32 } }

impl SourceSpan {
    pub(super) fn rebase(&self, current_item: Span, owner: LocalDefId) -> Option<Span> {
        if current_item == DUMMY_SP || current_item.ctxt() != SyntaxContext::root()
            || current_item.parent().is_some() { return None; }
        let span = match *self {
            Self::Dummy => DUMMY_SP,
            Self::Relative { lo, hi } => {
                if lo > hi || hi > (current_item.hi() - current_item.lo()).0 { return None; }
                Span::new(current_item.lo() + BytePos(lo), current_item.lo() + BytePos(hi),
                    SyntaxContext::root(), None)
            }
        };
        Some(span.with_parent(Some(owner)))
    }
}

#[derive(Encodable, Decodable)]
pub(super) struct Node { pub local: u32, pub span: SourceSpan }
#[derive(Encodable, Decodable)]
pub(super) struct Ident { pub text: String, pub span: SourceSpan }
#[derive(Encodable, Decodable)]
pub(super) enum Resolution { Primitive(PrimTy), Local(u32), MissingSegment }
#[derive(Encodable, Decodable)]
pub(super) struct Path {
    pub span: SourceSpan,
    pub resolution: Resolution,
    pub segment_local: u32,
    pub segment_ident: Ident,
    pub segment_resolution: Resolution,
    pub infer_args: bool,
}
#[derive(Encodable, Decodable)]
pub(super) struct Ty { pub node: Node, pub path: Path }
#[derive(Encodable, Decodable)]
pub(super) enum PatternKind { Wild, Binding { binding_local: u32, ident: Ident } }
#[derive(Encodable, Decodable)]
pub(super) struct Pattern { pub node: Node, pub kind: PatternKind }
#[derive(Encodable, Decodable)]
pub(super) enum Literal {
    Bool(bool), Byte(u8), Char(char), Int(u128, LitIntType), Float(String, LitFloatType),
}
#[derive(Encodable, Decodable)]
pub(super) enum Unary { Not, Neg }
#[derive(Encodable, Decodable)]
pub(super) enum ExprKind {
    Literal(SourceSpan, Literal), LocalPath(Path), Unit,
    Unary(Unary, Box<Expr>),
    Binary(BinOpKind, SourceSpan, Box<Expr>, Box<Expr>),
    Block(Block), Return(Option<Box<Expr>>),
}
#[derive(Encodable, Decodable)]
pub(super) struct Expr { pub node: Node, pub kind: ExprKind }
#[derive(Encodable, Decodable)]
pub(super) enum StatementKind {
    Let { node: Node, pat: Pattern, ty: Option<Ty>, init: Option<Expr> },
    Expr(Expr), Semi(Expr),
}
#[derive(Encodable, Decodable)]
pub(super) struct Statement { pub node: Node, pub kind: StatementKind }
#[derive(Encodable, Decodable)]
pub(super) struct Block {
    pub node: Node, pub statements: Vec<Statement>, pub tail: Option<Box<Expr>>,
}
#[derive(Encodable, Decodable)]
pub(super) struct Param { pub node: Node, pub ty_span: SourceSpan, pub pat: Pattern }
#[derive(Encodable, Decodable)]
pub(super) enum ReturnType { Default(SourceSpan), Primitive(Ty) }
#[derive(Encodable, Decodable)]
pub(super) struct OwnerTree {
    pub ident: Ident,
    pub span: SourceSpan,
    pub vis_span: SourceSpan,
    pub signature_span: SourceSpan,
    pub generics_span: SourceSpan,
    pub where_span: SourceSpan,
    pub lifetime_elision_allowed: bool,
    pub input_types: Vec<Ty>,
    pub output_type: ReturnType,
    pub params: Vec<Param>,
    pub value: Expr,
    pub local_id_limit: u32,
}

pub(super) fn rebase_hir_id(local: u32, limit: u32, owner: LocalDefId) -> Option<rustc_hir::HirId> {
    if local >= limit || limit == 0 || limit > 4096 { return None; }
    Some(rustc_hir::HirId { owner: rustc_hir::OwnerId { def_id: owner },
        local_id: rustc_hir::ItemLocalId::from_u32(local) })
}
