#![feature(rustc_private)]
extern crate rustc_ast;
extern crate rustc_data_structures;
extern crate rustc_driver;
extern crate rustc_hir;
extern crate rustc_interface;
extern crate rustc_macros;
extern crate rustc_middle;
extern crate rustc_serialize;
extern crate rustc_session;
extern crate rustc_span;

use std::collections::BTreeMap;
use std::fmt::Write as _;
use std::fs::OpenOptions;
use std::hash::Hasher;
use std::io::Write as _;
use std::path::PathBuf;
use std::process::ExitCode;
use std::time::{Instant,SystemTime,UNIX_EPOCH};
use rustc_ast as ast;
use rustc_ast::node_id::NodeSet;
use rustc_ast::visit::{self,Visitor};
use rustc_data_structures::stable_hash::StableHasher;
use rustc_data_structures::fingerprint::Fingerprint;
use rustc_data_structures::profiling::{TimePassesFormat,get_resident_set_size,print_time_passes_entry};
use rustc_driver::{Callbacks,Compilation,TimePassesCallbacks};
use rustc_interface::interface;
use rustc_middle::middle::resolve::ResolverAstLowering;
use rustc_middle::ty::TyCtxt;
use rustc_serialize::{Encodable,opaque::mem_encoder::MemEncoder};
use rustc_span::def_id::LOCAL_CRATE;
mod gate;
mod binding;
const _:()={
    let source=include_bytes!("gate.rs");let frozen=include_bytes!("gate.snapshot");
    assert!(source.len()==frozen.len());let mut n=0;
    while n<source.len(){assert!(source[n]==frozen[n]);n+=1;}
};
fn json(s:&str)->String {
    let mut out=String::from("\"");
    for c in s.chars(){match c {'"'=>out.push_str("\\\""),'\\'=>out.push_str("\\\\"),'\n'=>out.push_str("\\n"),
        '\r'=>out.push_str("\\r"),'\t'=>out.push_str("\\t"),c if c<'\u{20}'=>{write!(out,"\\u{:04x}",c as u32).unwrap();},c=>out.push(c)}}
    out.push('"');out
}
fn object(items:Vec<(&str,String)>)->String {format!("{{{}}}",items.into_iter().map(|(k,v)|format!("{}:{}",json(k),v)).collect::<Vec<_>>().join(","))}
fn strings<'a>(items:impl IntoIterator<Item=&'a str>)->String {format!("[{}]",items.into_iter().map(json).collect::<Vec<_>>().join(","))}
fn hex(v:Fingerprint)->String {let(a,b)=v.split();format!("{:016x}{:016x}",a.as_u64(),b.as_u64())}
fn encoded<T:Encodable<MemEncoder>>(v:&T)->Vec<u8>{let mut e=MemEncoder::new();v.encode(&mut e);e.finish()}
#[derive(Default)]
struct Report {
    owners:Vec<String>,seen:NodeSet,problems:Vec<String>,counts:BTreeMap<String,BTreeMap<&'static str,usize>>,
    reasons:BTreeMap<String,usize>,resolver_owners:usize,unvisited:usize,incremental:bool,prior_errors:bool,crate_name:String,
}
struct Walk<'a,'tcx>{tcx:TyCtxt<'tcx>,resolver:&'a ResolverAstLowering<'tcx>,report:Report}
impl Walk<'_, '_>{
    fn owner(&mut self,id:ast::NodeId,kind:&str,body:Option<(&ast::Fn,rustc_span::Span,&'static str)>){
        if !self.report.seen.insert(id){self.report.problems.push(format!("duplicate owner {id:?}"));return;}
        let Some(owner)=self.resolver.owners.get(&id) else {self.report.problems.push(format!("missing owner {id:?}"));return;};
        let mut row=vec![("owner_def_path_hash",json(&hex(self.tcx.def_path_hash(owner.def_id.to_def_id()).0))),
            ("kind",json(kind)),("role",json(body.map_or("outside-body-hook",|(_,_,r)|r))),
            ("owner_name",json(body.map_or("",|(f,_,_)|f.ident.name.as_str()))),
            ("owner_maps",object(vec![("definitions",owner.node_id_to_def_id.len().to_string()),
              ("labels",owner.label_res_map.len().to_string()),("lifetimes",owner.lifetimes_res_map.len().to_string()),
              ("traits",owner.trait_map.len().to_string()),("imports",owner.import_res.iter().filter(|r|r.is_some()).count().to_string()),
              ("extra_lifetimes",owner.extra_lifetime_params_map.len().to_string())]))];
        let role=body.map_or(kind,|(_,_,r)|r).to_owned();
        let count=self.report.counts.entry(role).or_default();*count.entry("owners").or_default()+=1;
        let mut reason="outside-body-hook";let mut eligible=false;
        if let Some((f,span,role))=body {
            match gate::probe(self.tcx,self.resolver,id,span,f,role){
                Ok(probe)=>{
                    let bytes=encoded(&probe.input);let mut h=StableHasher::new();h.write(&bytes);
                    eligible=true;reason="structural-body-input-accepted";
                    for (key,value) in [("input_eligible",1),("body_source_bytes",probe.body_bytes),
                        ("encoded_input_bytes",bytes.len()),("body_ast_nodes",probe.body_nodes),
                        ("parameter_ast_nodes",probe.parameter_nodes),("trait_entries",probe.trait_entries),
                        ("trait_candidates",probe.trait_candidates),("external_resolutions",probe.external_resolutions)]{
                        *count.entry(key).or_default()+=value;row.push((key,value.to_string()));
                    }
                    row.push(("input_digest",json(&hex(h.finish()))));
                }
                Err(r)=>reason=r,
            }
        }
        row.push(("structural_body_input_eligible",eligible.to_string()));row.push(("reason",json(reason)));
        *self.report.reasons.entry(reason.to_owned()).or_default()+=1;self.report.owners.push(object(row));
    }
}
impl<'ast> Visitor<'ast> for Walk<'_, '_>{
    fn visit_crate(&mut self,c:&'ast ast::Crate){self.owner(ast::CRATE_NODE_ID,"crate",None);visit::walk_crate(self,c);}
    fn visit_item(&mut self,i:&'ast ast::Item){
        self.owner(i.id,i.kind.descr(),match &i.kind{ast::ItemKind::Fn(f)=>Some((f,i.span,"free-function")),_=>None});
        visit::walk_item(self,i);
    }
    fn visit_assoc_item(&mut self,i:&'ast ast::AssocItem,c:visit::AssocCtxt){
        let role=match c{visit::AssocCtxt::Trait=>"provided-trait-method",visit::AssocCtxt::Impl{of_trait:true}=>"trait-impl-method",visit::AssocCtxt::Impl{of_trait:false}=>"inherent-impl-method"};
        self.owner(i.id,"associated-item",match &i.kind{ast::AssocItemKind::Fn(f)=>Some((f,i.span,role)),_=>None});
        visit::walk_assoc_item(self,i,c);
    }
    fn visit_foreign_item(&mut self,i:&'ast ast::ForeignItem){self.owner(i.id,"foreign-item",None);visit::walk_item(self,i);}
    fn visit_nested_use_tree(&mut self,t:&'ast ast::UseTree,id:ast::NodeId){self.owner(id,"nested-use-tree",None);self.visit_use_tree(t);}
    fn visit_attribute(&mut self,_:&'ast ast::Attribute){}
}
#[derive(Default)]
struct Diagnostic{standard:TimePassesCallbacks,time_passes:Option<TimePassesFormat>,report:Option<Report>,after_analysis:bool,sysroot:String}
impl Callbacks for Diagnostic{
    fn config(&mut self,c:&mut interface::Config){
        self.standard.config(c);
        self.time_passes=(c.opts.prints.is_empty()&&c.opts.unstable_opts.time_passes).then_some(c.opts.unstable_opts.time_passes_format);
        c.opts.sysroot.default=PathBuf::from(env!("HIR_COVERAGE_PUBLIC_SYSROOT"));self.sysroot=c.opts.sysroot.path().display().to_string();
    }
    fn after_expansion<'tcx>(&mut self,_:&interface::Compiler,tcx:TyCtxt<'tcx>)->Compilation{
        let name=tcx.crate_name(LOCAL_CRATE).to_string();
        let report={let(r,c)=tcx.resolver_for_lowering();let r=r.borrow();let c=c.borrow();
            let mut walk=Walk{tcx,resolver:&r,report:Report{crate_name:name,resolver_owners:r.owners.len(),
                incremental:tcx.incr_comp_session.is_some(),prior_errors:tcx.dcx().has_errors().is_some(),..Report::default()}};
            walk.visit_crate(&c);walk.report.unvisited=r.owners.keys().filter(|id|!walk.report.seen.contains(id)).count();walk.report};
        self.report=Some(report);Compilation::Continue
    }
    fn after_analysis<'tcx>(&mut self,_:&interface::Compiler,_:TyCtxt<'tcx>)->Compilation{self.after_analysis=true;Compilation::Continue}
}
impl Diagnostic{
    fn output(&self,args:&[String],start:u128,ok:bool)->String{
        let r=self.report.as_ref();let usable=ok&&self.after_analysis&&r.is_some_and(|r|!r.prior_errors&&r.unvisited==0&&r.problems.is_empty());
        let counts=r.map_or_else(||"{}".to_string(),|r|format!("{{{}}}",r.counts.iter().map(|(k,c)|format!("{}:{}",json(k),object(c.iter().map(|(k,v)|(*k,v.to_string())).collect()))).collect::<Vec<_>>().join(",")));
        let reasons=r.map_or_else(||"{}".to_string(),|r|object(r.reasons.iter().map(|(k,v)|(k.as_str(),v.to_string())).collect()));
        let rows=r.map_or_else(String::new,|r|r.owners.join(","));
        object(vec![("policy",json(gate::POLICY)),("gate_sha256",json(binding::GATE_SHA256)),("compiler_commit",json(binding::PUBLIC_COMMIT)),
            ("pid",std::process::id().to_string()),("started_unix_ns",start.to_string()),("compiler_argv",strings(args.iter().map(String::as_str))),
            ("effective_sysroot",json(&self.sysroot)),("crate_name",json(r.map_or("",|r|&r.crate_name))),
            ("ordinary_compiler_succeeded",ok.to_string()),("coverage_usable",usable.to_string()),("after_expansion_seen",r.is_some().to_string()),
            ("after_analysis_seen",self.after_analysis.to_string()),("incremental_session",r.is_some_and(|r|r.incremental).to_string()),
            ("resolver_owners",r.map_or(0,|r|r.resolver_owners).to_string()),("unvisited_resolver_owners",r.map_or(0,|r|r.unvisited).to_string()),
            ("owners",format!("[{rows}]")),("counts",counts),("reasons",reasons),
            ("problems",strings(r.into_iter().flat_map(|r|r.problems.iter().map(String::as_str)))),
            ("cache_effects_qualified","false".into()),("hir_ids_observed","false".into()),("cache_hits_measured","false".into()),("benchmark","false".into())])+"\n"
    }
}
fn main()->ExitCode{
    let started=Instant::now();let rss=get_resident_set_size();let start=SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_nanos();
    let early=rustc_session::EarlyDiagCtxt::new(rustc_session::config::ErrorOutputType::default());
    rustc_driver::init_rustc_env_logger(&early);rustc_driver::install_ice_hook(rustc_driver::DEFAULT_BUG_REPORT_URL,|_|());
    rustc_driver::install_ctrlc_handler();
    if !rustc_interface::util::rustc_version_str().unwrap_or("").contains("(cea272fa3 "){eprintln!("body coverage requires pinned public rustc");return ExitCode::from(2);}
    let mut args=rustc_driver::args::raw_args(&early);
    if std::env::var_os("HIR_BODY_COVERAGE_WRAPPER").is_some(){
        if args.get(1).map(String::as_str)!=Some(env!("HIR_COVERAGE_PUBLIC_RUSTC")){eprintln!("wrong body coverage compiler path");return ExitCode::from(2);}
        args.remove(1);
    }
    let Some(dir)=std::env::var_os("HIR_BODY_COVERAGE_OUTPUT") else {eprintln!("missing owned report output");return ExitCode::from(2);};
    let dir=PathBuf::from(dir);if !dir.is_dir(){eprintln!("owned output absent");return ExitCode::from(2);}
    let mut d=Diagnostic::default();let result=rustc_driver::catch_fatal_errors(||rustc_driver::run_compiler(&args,&mut d));
    if let Some(format)=d.time_passes{print_time_passes_entry("total",started.elapsed(),rss,get_resident_set_size(),format);}
    let out=d.output(&args,start,result.is_ok());let path=dir.join(format!("hir-body-coverage-{}-{start}.json",std::process::id()));
    if let Err(error)=OpenOptions::new().write(true).create_new(true).open(&path).and_then(|mut f|f.write_all(out.as_bytes())){
        eprintln!("cannot retain body coverage {}: {error}",path.display());return ExitCode::from(2);
    }
    if d.report.as_ref().is_some_and(|r|!r.problems.is_empty()){return ExitCode::from(2);}
    if result.is_ok(){ExitCode::SUCCESS}else{ExitCode::FAILURE}
}
