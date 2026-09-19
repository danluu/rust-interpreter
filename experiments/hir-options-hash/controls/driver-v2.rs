//! Uncompiled qualification source; execute only through a reviewed future plan.
#![feature(rustc_private)]

extern crate rustc_data_structures;
extern crate rustc_driver;
extern crate rustc_interface;
extern crate rustc_middle;

use std::path::PathBuf;
use std::sync::Barrier;

use rustc_data_structures::sync::{IntoDynSyncSend, is_dyn_thread_safe, par_join};
use rustc_driver::{Callbacks, Compilation};
use rustc_interface::interface;
use rustc_middle::ty::TyCtxt;

#[derive(Clone, Copy, Debug)]
struct Observation {
    incremental: u64,
    crate_hash: u64,
}

struct Control {
    label: &'static str,
    parallel: bool,
    observed: Option<Observation>,
}

impl Callbacks for Control {
    fn after_expansion<'tcx>(
        &mut self,
        _compiler: &interface::Compiler,
        tcx: TyCtxt<'tcx>,
    ) -> Compilation {
        assert!(self.observed.is_none(), "callback repeated");
        let expected = tcx.sess.opts.dep_tracking_hash(false).as_u64();
        let crate_hash = tcx.sess.opts.dep_tracking_hash(true).as_u64();
        assert!(!tcx.sess.opts.unstable_opts.hir_body_cache_capture);
        assert!(!tcx.sess.opts.unstable_opts.hir_body_cache_reuse);
        let threads = if self.parallel {
            assert!(is_dyn_thread_safe());
            // All cases run with -Zthreads=2. HIR reuse is off, so production
            // lowering cannot initialize the candidate cache before this call.
            let barrier = IntoDynSyncSend(Barrier::new(2));
            let read = || {
                barrier.wait();
                for _ in 0..64 {
                    assert_eq!(tcx.incremental_options_hash().as_u64(), expected);
                }
                std::thread::current().id()
            };
            let (left, right) = par_join(read, read);
            assert_ne!(left, right, "parallel control did not use distinct workers");
            2
        } else {
            assert!(!is_dyn_thread_safe());
            for _ in 0..64 {
                assert_eq!(tcx.incremental_options_hash().as_u64(), expected);
            }
            1
        };
        self.observed = Some(Observation { incremental: expected, crate_hash });
        println!(
            "{{\"label\":\"{}\",\"incremental_hash\":{},\"crate_hash\":{},\"workers\":{},\"status\":\"passed\"}}",
            self.label, expected, crate_hash, threads
        );
        Compilation::Stop
    }
}

fn main() {
    let args: Vec<_> = std::env::args().collect();
    assert_eq!(args.len(), 5, "driver <sysroot> <fixture.rs> <owned-output-dir> <serial|parallel>");
    let sysroot = PathBuf::from(&args[1]).canonicalize().unwrap();
    let source = PathBuf::from(&args[2]).canonicalize().unwrap();
    let output = PathBuf::from(&args[3]).canonicalize().unwrap();
    let parallel = match args[4].as_str() {
        "serial" => false,
        "parallel" => true,
        _ => panic!("unknown control mode"),
    };
    // Keep output path, source, and all other tracked options constant between
    // contexts. Do not change rustc's process-global dyn-thread-safe mode.
    let cases: [(&str, &[&str]); 8] = [
        ("base-first", &["-Copt-level=0", "-Aunused_variables"]),
        ("base-repeat", &["-Copt-level=0", "-Aunused_variables"]),
        ("tracked-change", &["-Copt-level=1", "-Aunused_variables"]),
        ("base-after-tracked", &["-Copt-level=0", "-Aunused_variables"]),
        ("non-crate-tracked-change", &["-Copt-level=0", "-Wunused_variables"]),
        ("base-after-lint", &["-Copt-level=0", "-Aunused_variables"]),
        ("untracked-change", &["-Copt-level=0", "-Aunused_variables", "-Zself-profile-events=default"]),
        ("base-final", &["-Copt-level=0", "-Aunused_variables"]),
    ];
    let mut observations = Vec::new();
    for (label, flags) in cases {
        let mut command = vec!["hash-cache-control".into(), source.display().to_string(),
            "--crate-name=hash_cache_control".into(), "--crate-type=lib".into(),
            "--edition=2024".into(), "--emit=metadata".into(), "--sysroot".into(),
            sysroot.display().to_string(), "--out-dir".into(), output.display().to_string()];
        command.extend(flags.iter().map(|value| (*value).to_owned()));
        if parallel {
            command.push("-Zthreads=2".into());
        }
        let mut control = Control { label, parallel, observed: None };
        rustc_driver::run_compiler(&command, &mut control);
        observations.push(control.observed.expect("compiler callback did not execute"));
    }
    let original = observations[0];
    for index in [1, 3, 5, 6, 7] {
        assert_eq!(observations[index].incremental, original.incremental);
        assert_eq!(observations[index].crate_hash, original.crate_hash);
    }
    assert_ne!(observations[2].incremental, original.incremental);
    assert_ne!(observations[2].crate_hash, original.crate_hash);
    assert_ne!(observations[4].incremental, original.incremental);
    assert_eq!(observations[4].crate_hash, original.crate_hash);
    println!("{{\"status\":\"passed\",\"contexts\":8,\"parallel\":{parallel}}}");
}
