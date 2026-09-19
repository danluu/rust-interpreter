//! Closed, owned body wire tree. No compiler IDs, pointers, symbols or hygiene
//! indices are deserialized. Unknown HIR variants/fields fall back at capture.
use serde::{Deserialize, Serialize};

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub(super) enum SourceSpan { Dummy, Relative { lo: u32, hi: u32 } }

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub(super) struct Node { pub relative: u32, pub span: SourceSpan }

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub(super) struct Ident { pub text: String, pub span: SourceSpan }

#[derive(Clone, Debug, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub(super) enum LocalRef { Body(u32), Parameter(u32) }

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub(super) enum Resolution {
    Local(LocalRef),
    /// Index of a nonlocal (non-binding) resolution in the freshly resolved
    /// exact input. Its DefKind/DefPathHash are already bound by that input key.
    /// Validation binds this to the current actual Res/DefId without decoding
    /// an old DefId or reconstructing a DefKind from unchecked bytes.
    Input(u32),
    /// Stock missing path-segment resolution. Never a value-path resolution.
    MissingSegment,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub(super) struct Segment {
    pub relative: u32, pub ident: Ident, pub resolution: Resolution, pub infer_args: bool,
}
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub(super) struct Path { pub span: SourceSpan, pub resolution: Resolution, pub segments: Vec<Segment> }

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub(super) enum Mutability { Immutable, Mutable }
#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub(super) enum ByRef { No, Yes { pinned: bool, mutability: Mutability } }
#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub(super) struct BindingMode { pub by_ref: ByRef, pub mutability: Mutability }

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub(super) enum PatternKind { Wild, Binding { mode: BindingMode, target: LocalRef, ident: Ident } }
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub(super) struct Pattern { pub node: Node, pub kind: PatternKind, pub default_binding_modes: bool }

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub(super) enum StringStyle { Cooked, Raw(u8) }
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub(super) enum Literal {
    String(String, StringStyle), Bytes(Vec<u8>, StringStyle), CString(Vec<u8>, StringStyle),
    Bool(bool), Byte(u8), Char(char), Integer(String, Option<String>), Float(String, Option<String>),
}
#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub(super) enum Unary { Not, Negate, Dereference }
#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub(super) enum Borrow { Reference, Raw }
#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub(super) enum BlockRules { Default, UnsafeUser }

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub(super) enum ExprKind {
    Array(Vec<Expr>), Tuple(Vec<Expr>),
    Literal { span: SourceSpan, value: Literal }, Path(Path),
    Call { function: Box<Expr>, arguments: Vec<Expr> },
    Method { segment: Segment, receiver: Box<Expr>, arguments: Vec<Expr>, span: SourceSpan },
    Unary(Unary, Box<Expr>),
    Binary { operation: String, span: SourceSpan, left: Box<Expr>, right: Box<Expr> },
    Block(Block),
    If { condition: Box<Expr>, then: Box<Expr>, otherwise: Option<Box<Expr>> },
    Assign { left: Box<Expr>, right: Box<Expr>, span: SourceSpan },
    AssignOp { operation: String, span: SourceSpan, left: Box<Expr>, right: Box<Expr> },
    Field(Box<Expr>, Ident), Index { value: Box<Expr>, index: Box<Expr>, span: SourceSpan },
    Borrow { kind: Borrow, mutability: Mutability, value: Box<Expr> }, Return(Option<Box<Expr>>),
}
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub(super) struct Expr { pub node: Node, pub kind: ExprKind }

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub(super) struct Local { pub node: Node, pub pattern: Pattern, pub init: Option<Expr> }
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub(super) enum StatementKind { Let(Local), Expr(Expr), Semi(Expr) }
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub(super) struct Statement { pub node: Node, pub kind: StatementKind }
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub(super) struct Block {
    pub node: Node, pub statements: Vec<Statement>, pub tail: Option<Box<Expr>>,
    pub rules: BlockRules, pub targeted_by_break: bool,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub(super) struct BodyTree { pub value: Expr }

pub(super) fn integer_type(name: &str) -> bool {
    matches!(name, "i8"|"i16"|"i32"|"i64"|"i128"|"isize"|"u8"|"u16"|"u32"|"u64"|"u128"|"usize")
}
pub(super) fn float_type(name: &str) -> bool { matches!(name, "f16"|"f32"|"f64"|"f128") }
pub(super) fn binary(name: &str) -> bool {
    matches!(name, "+"|"-"|"*"|"/"|"%"|"&&"|"||"|"^"|"&"|"|"|"<<"|">>"|"=="|"!="|"<"|"<="|">"|">=")
}
pub(super) fn assignment(name: &str) -> bool {
    // This pin keeps ast::AssignOpKind in HIR, including the equals sign.
    matches!(name, "+="|"-="|"*="|"/="|"%="|"^="|"&="|"|="|"<<="|">>=")
}

#[cfg(test)]
mod tests {
    #[test]
    fn assign_op_preserves_actual_pinned_hir_enum_spelling() {
        use rustc_hir::AssignOpKind::*;
        assert_eq!(AddAssign.as_str(), "+=");
        for op in [AddAssign, SubAssign, MulAssign, DivAssign, RemAssign,
            BitXorAssign, BitAndAssign, BitOrAssign, ShlAssign, ShrAssign] {
            assert!(super::assignment(op.as_str()));
        }
        for op in ["+", "==", "&&", "||", "<"] { assert!(!super::assignment(op)); }
    }
}
