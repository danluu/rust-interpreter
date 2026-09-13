//! Closed structural/resolved body gate. No lowering, queries, arena writes or cache.
use rustc_ast as ast;
use rustc_ast::node_id::NodeMap;
use rustc_hir::def::{DefKind, Res};
use rustc_macros::Encodable;
use rustc_middle::middle::resolve::ResolverAstLowering;
use rustc_middle::ty::TyCtxt;
use rustc_serialize::{Encodable, opaque::mem_encoder::MemEncoder};
use rustc_span::def_id::{DefId, DefPathHash};
use rustc_span::{Ident, Span, StableSourceFileId, SyntaxContext, DUMMY_SP};

pub const POLICY: &str = "hir-body-input-coverage-v2";
pub type Outcome<T> = Result<T, &'static str>;
#[derive(Debug, Encodable)]
pub enum Atom {
    Tag(&'static str), Count(usize), Text(String), Value(Vec<u8>),
    Span(Option<(u32,u32)>), Node(u32), Def(DefPathHash), Local(u32),
}
#[derive(Debug, Encodable)]
pub struct Input {
    pub owner: DefPathHash,
    pub file: StableSourceFileId,
    pub role: &'static str,
    pub owner_source: String,
    pub atoms: Vec<Atom>,
}
pub struct Probe {
    pub input: Input,
    pub body_bytes: usize,
    pub body_nodes: usize,
    pub parameter_nodes: usize,
    pub trait_entries: usize,
    pub trait_candidates: usize,
    pub external_resolutions: usize,
}
struct Walk<'a,'tcx> {
    tcx: TyCtxt<'tcx>, resolver: &'a ResolverAstLowering<'tcx>, owner: ast::NodeId,
    base: Span, atoms: Vec<Atom>, nodes: NodeMap<u32>, ordered: Vec<(ast::NodeId,bool)>,
    trait_entries: usize, trait_candidates: usize, external_resolutions: usize, depth: usize,
}
impl Walk<'_, '_> {
    fn tag(&mut self,v:&'static str) { self.atoms.push(Atom::Tag(v)); }
    fn count(&mut self,v:usize) { self.atoms.push(Atom::Count(v)); }
    fn value<T: Encodable<MemEncoder>>(&mut self,v:&T) {
        let mut e=MemEncoder::new();v.encode(&mut e);self.atoms.push(Atom::Value(e.finish()));
    }
    fn def(&mut self,id:DefId) {
        self.atoms.push(Atom::Def(self.tcx.def_path_hash(id)));
        self.external_resolutions+=usize::from(!id.is_local());
    }
    fn span(&mut self,span:Span)->Outcome<()> {
        if span==DUMMY_SP { self.atoms.push(Atom::Span(None));return Ok(()); }
        if span.ctxt()!=SyntaxContext::root() { return Err("nonroot-hygiene"); }
        if span.parent().is_some() { return Err("parented-input-span"); }
        if !self.base.contains(span) { return Err("span-outside-owner"); }
        self.atoms.push(Atom::Span(Some(((span.lo()-self.base.lo()).0,(span.hi()-self.base.lo()).0))));
        Ok(())
    }
    fn ident(&mut self,ident:Ident)->Outcome<()> {
        if ident.name.as_str().len()>4096 { return Err("identifier-budget"); }
        self.atoms.push(Atom::Text(ident.name.as_str().to_owned()));self.span(ident.span)
    }
    fn node(&mut self,id:ast::NodeId,body:bool)->Outcome<()> {
        if id==ast::DUMMY_NODE_ID { return Err("dummy-node"); }
        if self.nodes.contains_key(&id) { return Err("duplicate-node"); }
        if self.ordered.len()>=8192 { return Err("node-budget"); }
        if body {
            let o=&self.resolver.owners[&self.owner];
            if o.node_id_to_def_id.contains_key(&id) { return Err("body-existing-nonowner-definition"); }
            if o.lifetimes_res_map.contains_key(&id) { return Err("body-lifetime-resolution"); }
            if o.extra_lifetime_params_map.contains_key(&id) { return Err("body-extra-lifetime-parameters"); }
            if o.label_res_map.contains_key(&id) { return Err("body-label-resolution"); }
        }
        let n=self.ordered.len() as u32;self.nodes.insert(id,n);self.ordered.push((id,body));
        self.atoms.push(Atom::Node(n));self.value(&body);Ok(())
    }
    fn pattern(&mut self,p:&ast::Pat,body:bool)->Outcome<()> {
        let ast::Pat { id,kind,span }=p;
        self.node(*id,body)?;self.span(*span)?;
        match kind {
            ast::PatKind::Wild=>self.tag("wild"),
            ast::PatKind::Ident(mode,ident,None)=>{
                let Some(Res::Local(binding))=self.resolver.partial_res_map.get(id).and_then(|p|p.full_res())
                    else { return Err("pattern-not-local-binding"); };
                if binding!=*id { return Err("shared-pattern-binding"); }
                self.tag("binding");self.value(mode);self.ident(*ident)?;
            }
            _=>return Err("unsupported-pattern"),
        }
        Ok(())
    }
    fn segment(&mut self,s:&ast::PathSegment)->Outcome<()> {
        let ast::PathSegment { ident,id,args }=s;
        if args.is_some() { return Err("explicit-path-arguments"); }
        self.node(*id,true)?;self.ident(*ident)
    }
    fn path(&mut self,id:ast::NodeId,p:&ast::Path)->Outcome<()> {
        let ast::Path {span,segments}=p;
        let Some(res)=self.resolver.partial_res_map.get(&id).and_then(|p|p.full_res())
            else { return Err("incomplete-path-resolution"); };
        match res {
            Res::Local(_) | Res::SelfCtor(_) => (),
            Res::Def(DefKind::Fn | DefKind::AssocFn | DefKind::Const {..} | DefKind::AssocConst {..}
                | DefKind::Static {..} | DefKind::Ctor(..),_)=>(),
            _=>return Err("unsupported-value-resolution"),
        }
        if segments.is_empty() { return Err("empty-path"); }
        self.span(*span)?;self.count(segments.len());
        for segment in segments { self.segment(segment)?; }
        Ok(())
    }
    fn exprs(&mut self,values:&[Box<ast::Expr>])->Outcome<()> {
        self.count(values.len());for v in values { self.expr(v)?; }Ok(())
    }
    fn place(e:&ast::Expr)->bool {
        matches!(&e.kind,ast::ExprKind::Path(None,_)|ast::ExprKind::Field(..)|ast::ExprKind::Index(..)
            |ast::ExprKind::Unary(ast::UnOp::Deref,_))
    }
    fn expr(&mut self,e:&ast::Expr)->Outcome<()> {
        if self.depth>=128 {return Err("expression-depth-budget");}
        self.depth+=1;let result=self.expr_inner(e);self.depth-=1;result
    }
    fn expr_inner(&mut self,e:&ast::Expr)->Outcome<()> {
        let ast::Expr {id,kind,span,attrs,tokens}=e;
        if !attrs.is_empty() { return Err("body-expression-attributes"); }
        if tokens.is_some() { return Err("body-expression-tokens"); }
        self.node(*id,true)?;self.span(*span)?;
        match kind {
            ast::ExprKind::Array(v)=>{self.tag("array");self.exprs(v)?;}
            ast::ExprKind::Tup(v)=>{self.tag("tuple");self.exprs(v)?;}
            ast::ExprKind::Lit(lit)=>{
                if ast::LitKind::from_token_lit(*lit).is_err() { return Err("invalid-literal"); }
                if lit.symbol.as_str().len()>131072 { return Err("literal-budget"); }
                self.tag("literal");self.value(&lit.kind);
                self.atoms.push(Atom::Text(lit.symbol.as_str().to_owned()));
                self.value(&lit.suffix.is_some());
                if let Some(suffix)=lit.suffix { self.atoms.push(Atom::Text(suffix.as_str().to_owned())); }
            }
            ast::ExprKind::Path(None,p)=>{self.tag("path");self.path(*id,p)?;}
            ast::ExprKind::Call(f,args)=>{
                // Stock legacy rewriting only examines a bare Path with no final
                // generic args. No metadata lookup is hidden in this diagnostic.
                if let ast::ExprKind::Path(None,p)=&f.kind {
                    if p.segments.last().is_some_and(|s|s.args.is_none()) {
                        if let Some(def)=self.resolver.partial_res_map.get(&f.id)
                            .and_then(|p|p.full_res()).and_then(|r|r.opt_def_id()) {
                            if !def.is_local() { return Err("external-call-needs-current-legacy-proof"); }
                        }
                    }
                }
                self.tag("call");self.expr(f)?;self.exprs(args)?;
            }
            ast::ExprKind::MethodCall(call)=>{
                let ast::MethodCall {seg,receiver,args,span}= &**call;
                self.tag("method-call");self.segment(seg)?;self.expr(receiver)?;self.exprs(args)?;self.span(*span)?;
            }
            ast::ExprKind::Field(v,ident)=>{self.tag("field");self.expr(v)?;self.ident(*ident)?;}
            ast::ExprKind::Index(a,b,span)=>{self.tag("index");self.expr(a)?;self.expr(b)?;self.span(*span)?;}
            ast::ExprKind::Binary(op,a,b)=>{self.tag("binary");self.value(&op.node);self.span(op.span)?;self.expr(a)?;self.expr(b)?;}
            ast::ExprKind::Unary(op,v)=>{self.tag("unary");self.value(op);self.expr(v)?;}
            ast::ExprKind::AddrOf(kind,mutable,v)=>{
                if *kind==ast::BorrowKind::Pin { return Err("pinned-borrow"); }
                self.tag("borrow");self.value(kind);self.value(mutable);self.expr(v)?;
            }
            ast::ExprKind::Assign(a,b,span)=>{
                if !Self::place(a) { return Err("destructuring-assignment"); }
                self.tag("assign");self.expr(a)?;self.expr(b)?;self.span(*span)?;
            }
            ast::ExprKind::AssignOp(op,a,b)=>{
                if !Self::place(a) { return Err("destructuring-assignment"); }
                self.tag("assign-op");self.value(&op.node);self.span(op.span)?;self.expr(a)?;self.expr(b)?;
            }
            ast::ExprKind::If(c,b,e)=>{
                self.tag("if");self.expr(c)?;self.block(b)?;self.value(&e.is_some());
                if let Some(e)=e {self.expr(e)?;}
            }
            ast::ExprKind::Block(b,None)=>{self.tag("block-expr");self.block(b)?;}
            ast::ExprKind::Ret(v)=>{self.tag("return");self.value(&v.is_some());if let Some(v)=v {self.expr(v)?;}}
            ast::ExprKind::Paren(v)=>{self.tag("paren");self.expr(v)?;}
            _=>return Err("unsupported-expression"),
        }
        Ok(())
    }
    fn block(&mut self,b:&ast::Block)->Outcome<()> {
        let ast::Block {stmts,id,rules,span}=b;
        if !matches!(rules,ast::BlockCheckMode::Default|ast::BlockCheckMode::Unsafe(ast::UnsafeSource::UserProvided)) {
            return Err("generated-unsafe-block");
        }
        self.node(*id,true)?;self.span(*span)?;self.value(rules);self.count(stmts.len());
        for s in stmts {
            let ast::Stmt {id,kind,span}=s;
            self.node(*id,true)?;self.span(*span)?;
            match kind {
                ast::StmtKind::Empty=>self.tag("empty"),
                ast::StmtKind::Expr(e)=>{self.tag("expr-stmt");self.expr(e)?;}
                ast::StmtKind::Semi(e)=>{self.tag("semi-stmt");self.expr(e)?;}
                ast::StmtKind::Let(l)=>{
                    let ast::Local {id,super_,pat,ty,kind,span,colon_sp,attrs,tokens}=&**l;
                    if super_.is_some()||ty.is_some()||colon_sp.is_some() {return Err("body-local-type-or-super");}
                    if !attrs.is_empty()||tokens.is_some() {return Err("body-local-attributes-or-tokens");}
                    self.tag("let");self.node(*id,true)?;self.span(*span)?;
                    match kind {
                        ast::LocalKind::Decl=>self.tag("uninitialized"),
                        ast::LocalKind::Init(e)=>{self.tag("initialized");self.expr(e)?;}
                        _=>return Err("let-else"),
                    }
                    self.pattern(pat,true)?;
                }
                _=>return Err("nested-item-or-unexpanded-statement"),
            }
        }
        Ok(())
    }
    fn resolution(&mut self,r:Res<ast::NodeId>)->Outcome<()> {
        match r {
            Res::Local(id)=>{self.tag("local");self.atoms.push(Atom::Local(*self.nodes.get(&id).ok_or("binding-outside-input")?));}
            Res::Def(kind,id)=>{self.tag("definition");self.value(&kind);self.def(id);}
            Res::PrimTy(t)=>{self.tag("primitive");self.value(&t);}
            Res::SelfCtor(id)=>{self.tag("self-constructor");self.def(id);}
            Res::SelfTyParam{trait_}=>{self.tag("self-trait-type");self.def(trait_);}
            Res::SelfTyAlias{alias_to,is_trait_impl}=>{self.tag("self-impl-type");self.def(alias_to);self.value(&is_trait_impl);}
            Res::Err=>return Err("error-resolution"),
            _=>return Err("unsupported-resolution"),
        }
        Ok(())
    }
    fn resolved(&mut self)->Outcome<()> {
        for (id,body) in self.ordered.clone() {
            self.tag("node-resolution");self.value(&body);
            if let Some(partial)=self.resolver.partial_res_map.get(&id).copied() {
                self.value(&true);self.count(partial.unresolved_segments());
                // Full Expr paths required above; method segments may be absent
                // and type checking will select their current trait candidate.
                self.resolution(partial.base_res())?;
            } else {self.value(&false);}
            let owner=&self.resolver.owners[&self.owner];
            if body {
                if let Some(traits)=owner.trait_map.get(&id).copied() {
                    self.tag("trait-entry");self.count(traits.len());self.trait_entries+=1;
                    for candidate in traits {
                        self.trait_candidates+=1;self.def(candidate.def_id);self.count(candidate.import_ids.len());
                        for id in candidate.import_ids {self.def(id.to_def_id());}
                        self.value(&candidate.lint_ambiguous);
                    }
                } else {self.tag("no-trait-entry");}
            }
        }
        Ok(())
    }
}

/// Caller enumerates Fn owners directly from expanded AST; no HIR query needed.
/// Accepted means structural input only, never an S/E or replay qualification.
pub fn probe<'tcx>(tcx:TyCtxt<'tcx>,resolver:&ResolverAstLowering<'tcx>,owner:ast::NodeId,
    span:Span,f:&ast::Fn,role:&'static str)->Outcome<Probe> {
    if tcx.incr_comp_session.is_none() {return Err("no-incremental-session");}
    if tcx.dcx().has_errors().is_some() {return Err("prior-errors");}
    if span==DUMMY_SP||span.ctxt()!=SyntaxContext::root()||span.parent().is_some() {return Err("owner-span-or-hygiene");}
    if f.sig.header.coroutine_marker.is_some() {return Err("coroutine-body");}
    if f.contract.is_some() {return Err("contract-body");}
    let body=f.body.as_deref().ok_or("no-body")?;
    let current=resolver.owners.get(&owner).ok_or("missing-resolver-owner")?;
    if current.id!=owner {return Err("owner-identity-mismatch");}
    let file=tcx.sess.source_map().lookup_source_file(span.lo());
    if !file.contains(span.hi())||(span.hi()-span.lo()).0>262144 {return Err("source-extent-budget");}
    let source=tcx.sess.source_map().span_to_snippet(span).map_err(|_|"owner-source-unavailable")?;
    let body_source=tcx.sess.source_map().span_to_snippet(body.span).map_err(|_|"body-source-unavailable")?;
    let mut w=Walk{tcx,resolver,owner,base:span,atoms:Vec::new(),nodes:NodeMap::default(),ordered:Vec::new(),
        trait_entries:0,trait_candidates:0,external_resolutions:0,depth:0};
    w.tag(POLICY);w.count(f.sig.decl.inputs.len());
    for p in &f.sig.decl.inputs {
        if p.is_placeholder {return Err("placeholder-parameter");}
        w.node(p.id,false)?;w.span(p.span)?;w.span(p.ty.span)?;w.pattern(&p.pat,false)?;
    }
    let parameter_nodes=w.ordered.len();w.block(body)?;w.resolved()?;
    let body_nodes=w.ordered.len()-parameter_nodes;
    Ok(Probe{input:Input{owner:tcx.def_path_hash(current.def_id.to_def_id()),file:file.stable_id,
        role,owner_source:source,atoms:w.atoms},body_bytes:body_source.len(),body_nodes,parameter_nodes,
        trait_entries:w.trait_entries,trait_candidates:w.trait_candidates,external_resolutions:w.external_resolutions})
}
