use serde::{Deserialize, Serialize};

#[derive(Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub(super) enum SourceSpan { Dummy, Relative { lo: u32, hi: u32 } }
#[derive(Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub(super) struct Node { pub local: u32, pub span: SourceSpan }
#[derive(Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub(super) struct Ident { pub text: String, pub span: SourceSpan }
#[derive(Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub(super) enum Resolution { Primitive(String), Local(u32), MissingSegment }
#[derive(Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub(super) struct Path {
    pub span: SourceSpan,
    pub resolution: Resolution,
    pub segment_local: u32,
    pub segment_ident: Ident,
    pub segment_resolution: Resolution,
    pub infer_args: bool,
}
#[derive(Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub(super) struct Ty { pub node: Node, pub path: Path }
#[derive(Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub(super) enum PatternKind { Wild, Binding { binding_local: u32, ident: Ident } }
#[derive(Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub(super) struct Pattern { pub node: Node, pub kind: PatternKind }
#[derive(Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub(super) enum Literal {
    Bool(bool), Byte(u8), Char(char), Int(String, Option<String>), Float(String, Option<String>),
}
#[derive(Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub(super) enum Unary { Not, Neg }
#[derive(Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub(super) enum ExprKind {
    Literal(SourceSpan, Literal), LocalPath(Path), Unit,
    Unary(Unary, Box<Expr>),
    Binary(String, SourceSpan, Box<Expr>, Box<Expr>),
    Block(Block), Return(Option<Box<Expr>>),
}
#[derive(Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub(super) struct Expr { pub node: Node, pub kind: ExprKind }
#[derive(Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub(super) enum StatementKind {
    Let { node: Node, pat: Pattern, ty: Option<Ty>, init: Option<Expr> },
    Expr(Expr), Semi(Expr),
}
#[derive(Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub(super) struct Statement { pub node: Node, pub kind: StatementKind }
#[derive(Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub(super) struct Block {
    pub node: Node, pub statements: Vec<Statement>, pub tail: Option<Box<Expr>>,
}
#[derive(Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub(super) struct Param { pub node: Node, pub ty_span: SourceSpan, pub pat: Pattern }
#[derive(Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub(super) enum ReturnType { Default(SourceSpan), Primitive(Ty) }
#[derive(Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
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

pub(super) fn primitive(name: &str) -> Option<rustc_hir::PrimTy> {
    rustc_hir::PrimTy::ALL.into_iter().find(|ty| ty.name_str() == name && name != "str")
}

pub(super) fn binary(name: &str) -> Option<rustc_ast::BinOpKind> {
    use rustc_ast::BinOpKind::*;
    [Add, Sub, Mul, Div, Rem, And, Or, BitXor, BitAnd, BitOr, Shl, Shr, Eq, Lt, Le, Ne, Ge, Gt]
        .into_iter().find(|op| op.as_str() == name)
}

pub(super) fn integer_type(name: &Option<String>) -> Option<rustc_ast::LitIntType> {
    use rustc_ast::LitIntType;
    Some(match name {
        None => LitIntType::Unsuffixed,
        Some(name) => match primitive(name)? {
            rustc_hir::PrimTy::Int(ty) => LitIntType::Signed(ty),
            rustc_hir::PrimTy::Uint(ty) => LitIntType::Unsigned(ty),
            _ => return None,
        },
    })
}

pub(super) fn float_type(name: &Option<String>) -> Option<rustc_ast::LitFloatType> {
    use rustc_ast::LitFloatType;
    Some(match name {
        None => LitFloatType::Unsuffixed,
        Some(name) => match primitive(name)? {
            rustc_hir::PrimTy::Float(ty) => LitFloatType::Suffixed(ty),
            _ => return None,
        },
    })
}
