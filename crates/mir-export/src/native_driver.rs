//! Preserve the public rustc startup hooks when adapting ordinary Cargo units.
//!
//! The pinned rustc executable also calls its private
//! `rustc_driver_impl::signal_handler::install` for fatal-signal diagnostics.
//! That hook is unavailable to external drivers. We retain the platform's
//! normal fatal-signal behavior rather than copying private signal machinery.
use crate::{borrowck_cache, wrapper_route::BorrowckCacheMode};
use rustc_data_structures::profiling::{
    TimePassesFormat, get_resident_set_size, print_time_passes_entry,
};
use rustc_driver::{Callbacks, Compilation, TimePassesCallbacks};
use rustc_interface::interface;
use rustc_middle::ty::TyCtxt;
use rustc_session::{EarlyDiagCtxt, config::ErrorOutputType};
use std::{process::ExitCode, time::Instant};

struct NativeCallbacks {
    standard: TimePassesCallbacks,
    cache: borrowck_cache::CheckCallbacks,
    time_passes: Option<TimePassesFormat>,
}

impl Callbacks for NativeCallbacks {
    fn config(&mut self, config: &mut interface::Config) {
        // This also preserves native rustc's trimmed diagnostic paths.
        self.standard.config(config);
        // TimePassesCallbacks keeps its format private. Match its pinned
        // condition exactly, including suppressing totals for --print queries.
        self.time_passes = (config.opts.prints.is_empty() && config.opts.unstable_opts.time_passes)
            .then_some(config.opts.unstable_opts.time_passes_format);
        self.cache.config(config);
    }

    fn after_analysis<'tcx>(
        &mut self,
        compiler: &interface::Compiler,
        tcx: TyCtxt<'tcx>,
    ) -> Compilation {
        self.cache.after_analysis(compiler, tcx)
    }
}

pub(crate) fn run(args: &[String], mode: BorrowckCacheMode) -> ExitCode {
    let started = Instant::now();
    let start_rss = get_resident_set_size();
    let early_dcx = EarlyDiagCtxt::new(ErrorOutputType::default());
    rustc_driver::init_rustc_env_logger(&early_dcx);
    rustc_driver::install_ice_hook(rustc_driver::DEFAULT_BUG_REPORT_URL, |_| ());
    rustc_driver::install_ctrlc_handler();
    let mut callbacks = NativeCallbacks {
        standard: TimePassesCallbacks::default(),
        cache: borrowck_cache::CheckCallbacks(mode),
        time_passes: None,
    };
    let status = rustc_driver::catch_with_exit_code(|| {
        rustc_driver::run_compiler(args, &mut callbacks)
    });
    if let Some(format) = callbacks.time_passes {
        let end_rss = get_resident_set_size();
        print_time_passes_entry("total", started.elapsed(), start_rss, end_rss, format);
    }
    borrowck_cache::report();
    status
}
