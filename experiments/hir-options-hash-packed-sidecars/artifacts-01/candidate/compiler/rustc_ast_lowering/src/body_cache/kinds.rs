//! Classify only IDs already admitted by the exact qualified walker. This is
//! an output cross-check, never a replacement structural eligibility gate.
use rustc_ast::{self as ast, node_id::NodeMap, visit::{self, Visitor}};

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(super) enum Expr {
    Array, Tuple, Literal, Path, Call, Method, Unary, Binary, Block, If,
    Assign, AssignOp, Field, Index, Borrow, Return, Parenthesized, Unsupported,
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(super) enum Statement { Let, Expr, Semi, Empty, Unsupported }
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(super) enum Kind {
    Expression(Expr), Statement(Statement), Pattern { binding: bool },
    Block, Local, Segment, Parameter, Unsupported,
}

struct Classify<'a> { ordinals: &'a NodeMap<u32>, result: Vec<Option<Kind>>, failed: bool }
impl Classify<'_> {
    fn mark(&mut self, id: ast::NodeId, kind: Kind) {
        if let Some(&ordinal) = self.ordinals.get(&id) {
            if self.result[ordinal as usize].replace(kind).is_some() { self.failed = true; }
        }
    }
}
impl<'ast> Visitor<'ast> for Classify<'_> {
    fn visit_expr(&mut self, value: &'ast ast::Expr) {
        let kind = match value.kind {
            ast::ExprKind::Array(..) => Expr::Array, ast::ExprKind::Tup(..) => Expr::Tuple,
            ast::ExprKind::Lit(..) => Expr::Literal, ast::ExprKind::Path(..) => Expr::Path,
            ast::ExprKind::Call(..) => Expr::Call, ast::ExprKind::MethodCall(..) => Expr::Method,
            ast::ExprKind::Unary(..) => Expr::Unary, ast::ExprKind::Binary(..) => Expr::Binary,
            ast::ExprKind::Block(..) => Expr::Block, ast::ExprKind::If(..) => Expr::If,
            ast::ExprKind::Assign(..) => Expr::Assign, ast::ExprKind::AssignOp(..) => Expr::AssignOp,
            ast::ExprKind::Field(..) => Expr::Field, ast::ExprKind::Index(..) => Expr::Index,
            ast::ExprKind::AddrOf(..) => Expr::Borrow, ast::ExprKind::Ret(..) => Expr::Return,
            ast::ExprKind::Paren(..) => Expr::Parenthesized, _ => Expr::Unsupported,
        };
        self.mark(value.id, Kind::Expression(kind)); visit::walk_expr(self, value);
    }
    fn visit_stmt(&mut self, value: &'ast ast::Stmt) {
        let kind = match value.kind {
            ast::StmtKind::Let(..) => Statement::Let, ast::StmtKind::Expr(..) => Statement::Expr,
            ast::StmtKind::Semi(..) => Statement::Semi, ast::StmtKind::Empty => Statement::Empty,
            _ => Statement::Unsupported,
        };
        self.mark(value.id, Kind::Statement(kind)); visit::walk_stmt(self, value);
    }
    fn visit_pat(&mut self, value: &'ast ast::Pat) {
        let kind = match value.kind {
            ast::PatKind::Wild => Kind::Pattern { binding: false },
            ast::PatKind::Ident(_, _, None) => Kind::Pattern { binding: true }, _ => Kind::Unsupported,
        };
        self.mark(value.id, kind); visit::walk_pat(self, value);
    }
    fn visit_block(&mut self, value: &'ast ast::Block) {
        self.mark(value.id, Kind::Block); visit::walk_block(self, value);
    }
    fn visit_local(&mut self, value: &'ast ast::Local) {
        self.mark(value.id, Kind::Local); visit::walk_local(self, value);
    }
    fn visit_path_segment(&mut self, value: &'ast ast::PathSegment) {
        self.mark(value.id, Kind::Segment); visit::walk_path_segment(self, value);
    }
    fn visit_param(&mut self, value: &'ast ast::Param) {
        self.mark(value.id, Kind::Parameter); visit::walk_param(self, value);
    }
}

pub(super) fn classify(function: &ast::Fn, ordinals: &NodeMap<u32>) -> Option<Vec<Kind>> {
    let mut visitor = Classify { ordinals, result: vec![None; ordinals.len()], failed: false };
    for parameter in &function.sig.decl.inputs { visitor.visit_param(parameter); }
    visitor.visit_block(function.body.as_deref()?);
    if visitor.failed { return None; }
    visitor.result.into_iter().collect()
}
