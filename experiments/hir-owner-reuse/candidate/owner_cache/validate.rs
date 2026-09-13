use std::collections::BTreeSet;

use super::wire::*;

pub(super) struct CheckedTree(OwnerTree);

impl CheckedTree {
    pub(super) fn get(&self) -> &OwnerTree { &self.0 }
    pub(super) fn into_inner(self) -> OwnerTree { self.0 }
}

struct Check<'a> {
    source: &'a str,
    limit: u32,
    ids: BTreeSet<u32>,
    bindings: BTreeSet<u32>,
    references: Vec<u32>,
    depth: usize,
}

impl Check<'_> {
    fn span(&self, span: &SourceSpan) -> Option<()> {
        match *span {
            SourceSpan::Dummy => Some(()),
            SourceSpan::Relative { lo, hi } if lo <= hi && hi as usize <= self.source.len()
                && self.source.is_char_boundary(lo as usize) && self.source.is_char_boundary(hi as usize)
                => Some(()),
            _ => None,
        }
    }
    fn text(&self, value: &str) -> Option<()> {
        (value.len() <= 65_536).then_some(())
    }
    fn ident(&self, value: &Ident) -> Option<()> {
        if value.text.is_empty() { return None; }
        self.text(&value.text)?;
        self.span(&value.span)
    }
    fn id(&mut self, id: u32) -> Option<()> {
        (id > 0 && id < self.limit && self.ids.insert(id)).then_some(())
    }
    fn node(&mut self, node: &Node) -> Option<()> {
        self.id(node.local)?;
        self.span(&node.span)
    }
    fn res(&mut self, res: &Resolution, segment: bool) -> Option<()> {
        match res {
            Resolution::Primitive(name) => { primitive(name)?; }
            Resolution::Local(id) => self.references.push(*id),
            Resolution::MissingSegment if segment => {}
            _ => return None,
        }
        Some(())
    }
    fn path(&mut self, path: &Path, is_type: bool) -> Option<()> {
        if path.infer_args == is_type { return None; }
        match (&path.resolution, is_type) {
            (Resolution::Primitive(_), true) | (Resolution::Local(_), false) => {}
            _ => return None,
        }
        self.span(&path.span)?;
        self.res(&path.resolution, false)?;
        self.id(path.segment_local)?;
        self.ident(&path.segment_ident)?;
        self.res(&path.segment_resolution, true)
    }
    fn ty(&mut self, ty: &Ty) -> Option<()> {
        self.node(&ty.node)?;
        self.path(&ty.path, true)
    }
    fn pat(&mut self, pat: &Pattern) -> Option<()> {
        self.node(&pat.node)?;
        if let PatternKind::Binding { binding_local, ident } = &pat.kind {
            if *binding_local != pat.node.local || !self.bindings.insert(*binding_local) { return None; }
            self.ident(ident)?;
        }
        Some(())
    }
    fn expr(&mut self, expr: &Expr) -> Option<()> {
        if self.depth >= 64 { return None; }
        self.depth += 1;
        let result = self.expr_inner(expr);
        self.depth -= 1;
        result
    }
    fn expr_inner(&mut self, expr: &Expr) -> Option<()> {
        self.node(&expr.node)?;
        match &expr.kind {
            ExprKind::Unit => {}
            ExprKind::Literal(span, value) => {
                self.span(span)?;
                match value {
                    Literal::Int(value, kind) => { value.parse::<u128>().ok()?; integer_type(kind)?; }
                    Literal::Float(value, kind) => {
                        self.text(value)?;
                        if !value.as_bytes().first().is_some_and(u8::is_ascii_digit)
                            || !value.bytes().all(|b| b.is_ascii_digit() || b".eE+-_".contains(&b))
                            || value.replace('_', "").parse::<f64>().is_err() { return None; }
                        float_type(kind)?;
                    }
                    _ => {}
                }
            }
            ExprKind::LocalPath(path) => self.path(path, false)?,
            ExprKind::Unary(_, value) => self.expr(value)?,
            ExprKind::Binary(op, span, left, right) => {
                binary(op)?;
                self.span(span)?;
                self.expr(left)?;
                self.expr(right)?;
            }
            ExprKind::Block(block) => self.block(block)?,
            ExprKind::Return(value) => if let Some(value) = value { self.expr(value)?; },
        }
        Some(())
    }
    fn block(&mut self, block: &Block) -> Option<()> {
        self.node(&block.node)?;
        if block.statements.len() > 512 { return None; }
        for stmt in &block.statements {
            self.node(&stmt.node)?;
            match &stmt.kind {
                StatementKind::Let { node, pat, ty, init } => {
                    self.node(node)?;
                    self.pat(pat)?;
                    if let Some(ty) = ty { self.ty(ty)?; }
                    if let Some(init) = init { self.expr(init)?; }
                }
                StatementKind::Expr(expr) | StatementKind::Semi(expr) => self.expr(expr)?,
            }
        }
        if let Some(tail) = &block.tail { self.expr(tail)?; }
        Some(())
    }
}

pub(super) fn check(tree: OwnerTree, source: &str) -> Option<CheckedTree> {
    if tree.local_id_limit == 0 || tree.local_id_limit > 4096 || source.len() > 65_536
        || tree.params.len() != tree.input_types.len() || tree.params.len() > 512
        || !matches!(tree.value.kind, ExprKind::Block(_)) { return None; }
    match tree.span {
        SourceSpan::Relative { lo: 0, hi } if hi as usize == source.len() => {}
        _ => return None,
    }
    let mut check = Check { source, limit: tree.local_id_limit, ids: BTreeSet::new(),
        bindings: BTreeSet::new(), references: Vec::new(), depth: 0 };
    check.ident(&tree.ident)?;
    for span in [&tree.span, &tree.vis_span, &tree.signature_span, &tree.generics_span, &tree.where_span] {
        check.span(span)?;
    }
    for ty in &tree.input_types { check.ty(ty)?; }
    match &tree.output_type {
        ReturnType::Default(span) => check.span(span)?,
        ReturnType::Primitive(ty) => check.ty(ty)?,
    }
    for param in &tree.params {
        check.node(&param.node)?;
        check.span(&param.ty_span)?;
        check.pat(&param.pat)?;
    }
    check.expr(&tree.value)?;
    if check.ids.len() != tree.local_id_limit as usize - 1
        || check.references.iter().any(|id| !check.bindings.contains(id)) { return None; }
    Some(CheckedTree(tree))
}
