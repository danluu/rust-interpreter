//! Uncompiled lifecycle control; requires the matching future compiler/B3 pair.
#![feature(rustc_private)]
extern crate rustc_driver;
extern crate rustc_interface;
extern crate rustc_middle;
extern crate rustc_session;
use std::path::{Path,PathBuf};
use rustc_driver::{Callbacks,Compilation};
use rustc_interface::interface;
use rustc_middle::ty::TyCtxt;
use rustc_session::hir_body_cache::Policy;
struct Control { stop:bool, observed:bool }
impl Callbacks for Control {
    fn after_analysis<'tcx>(&mut self,_:&interface::Compiler,tcx:TyCtxt<'tcx>)->Compilation {
        assert!(!self.observed); self.observed=true;
        assert!(tcx.sess.opts.unstable_opts.hir_body_cache_capture);
        let session=tcx.incr_comp_session.unwrap();
        assert!(session.session_directory.file_name().unwrap().to_str().unwrap().ends_with("-working"));
        // The future controller also requires an actual anchor capture event
        // before this callback, proving the body reached queue_record.
        for policy in [Policy::Capture,Policy::Reuse] {
            assert!(!session.session_directory.join(policy.filename()).exists());
        }
        println!("pack-lifecycle: after-analysis pending-publication stop={}",self.stop);
        if self.stop {Compilation::Stop} else {Compilation::Continue}
    }
}
fn packs(root:&Path,result:&mut Vec<PathBuf>) {
    for entry in std::fs::read_dir(root).unwrap() {
        let p=entry.unwrap().path(); assert!(!p.is_symlink());
        if p.is_dir() {packs(&p,result);}
        else if p.file_name().unwrap()==Policy::Capture.filename() {result.push(p);}
    }
}
fn main() {
    let args:Vec<_>=std::env::args().collect();
    assert_eq!(args.len(),5,"driver <sysroot> <fixture> <fresh-owned-output> <stop|continue>");
    assert!(std::env::var_os("RUSTC_FORCE_RUSTC_VERSION").is_none());
    let sysroot=PathBuf::from(&args[1]).canonicalize().unwrap();
    let fixture=PathBuf::from(&args[2]).canonicalize().unwrap();
    let output=PathBuf::from(&args[3]).canonicalize().unwrap();
    assert_eq!(std::fs::read_dir(&output).unwrap().count(),0);
    let stop=match args[4].as_str() {"stop"=>true,"continue"=>false,_=>panic!("unknown mode")};
    let mut control=Control {stop,observed:false};
    let command=vec!["packed-lifecycle-control".into(),fixture.display().to_string(),
        "--crate-name=packed_lifecycle_control".into(),"--crate-type=lib".into(),
        "--edition=2024".into(),"--emit=metadata".into(),"--sysroot".into(),sysroot.display().to_string(),
        "--out-dir".into(),output.display().to_string(),format!("-Cincremental={}",output.join("incremental").display()),
        "-Zhir-body-cache-capture=true".into(),"-Zhir-body-cache-reuse=false".into(),"-Zincremental-info=true".into()];
    rustc_driver::run_compiler(&command,&mut control); assert!(control.observed);
    let mut files=Vec::new(); packs(&output,&mut files);
    if stop {assert!(files.is_empty());} else {
        assert_eq!(files.len(),1);
        assert!(!files[0].parent().unwrap().file_name().unwrap().to_str().unwrap().ends_with("-working"));
        assert_eq!(&std::fs::read(&files[0]).unwrap()[..8],b"RHIRPK01");
    }
    println!("pack-lifecycle: passed stop={stop} published={}",files.len());
}
