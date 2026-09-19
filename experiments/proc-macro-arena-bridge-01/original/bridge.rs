//! Real bridge transport controls; link against the qualified native proc_macro.
//! This does not substitute for the rustc-server proc-macro fixtures beside it.
#![feature(proc_macro_internals, proc_macro_span, proc_macro_expand)]

extern crate proc_macro;

use proc_macro::bridge::{self, client::Client, server::{self, Server}};
use proc_macro::{Span, TokenStream};
use std::cell::Cell;
use std::ops::{Bound, Range};
use std::sync::{Arc, Mutex};

static SERIAL: Mutex<()> = Mutex::new(());
static CLIENT_THREADS: Mutex<Vec<(&str, std::thread::ThreadId)>> = Mutex::new(Vec::new());
thread_local! { static SAVED: Cell<Option<Span>> = const { Cell::new(None) }; }

#[derive(Default)]
struct Log { next: u32, drops: Vec<u32>, calls: Vec<(&'static str, u32)> }
type Shared = Arc<Mutex<Log>>;

#[derive(Default)]
struct Stream { id: u32, log: Option<Shared> }
impl Stream {
    fn new(log: &Shared) -> Self {
        let id = { let mut l = log.lock().unwrap(); l.next += 1; l.next };
        Self { id, log: Some(log.clone()) }
    }
}
impl Clone for Stream {
    fn clone(&self) -> Self { self.log.as_ref().map(Self::new).unwrap_or_default() }
}
impl Drop for Stream {
    fn drop(&mut self) {
        if let Some(log) = &self.log { log.lock().unwrap().drops.push(self.id); }
    }
}

struct FixtureServer { log: Shared, origin: u32, fail_line: bool }
impl FixtureServer {
    fn call(&self, name: &'static str, span: u32) { self.log.lock().unwrap().calls.push((name, span)); }
}

// Unsupported methods panic instead of returning invented successful results.
// Only methods explicitly asserted by these transport controls are implemented.
macro_rules! unsupported {
    ($(fn $name:ident($($arg:ident: $ty:ty),*) $(-> $ret:ty)?;)*) => {$(
        fn $name(&mut self, $($arg: $ty),*) $(-> $ret)? {
            $(let _ = &$arg;)*
            panic!(concat!("unexpected bridge method: ", stringify!($name)))
        }
    )*};
}
impl Server for FixtureServer {
    type TokenStream = Stream;
    type Span = u32;
    type Symbol = String;
    fn globals(&mut self) -> bridge::ExpnGlobals<u32> {
        bridge::ExpnGlobals { def_site: 100_000, call_site: self.origin, mixed_site: 200_000 }
    }
    fn intern_symbol(s: &str) -> String { s.to_owned() }
    fn with_symbol_string(s: &String, f: impl FnOnce(&str)) { f(s); }
    fn ts_drop(&mut self, stream: Stream) { drop(stream); }
    fn ts_clone(&mut self, stream: &Stream) -> Stream { stream.clone() }
    fn ts_expand_expr(&mut self, _stream: &Stream) -> Result<Stream, ()> {
        self.call("nested-enter", self.origin);
        let nested = FixtureServer { log: self.log.clone(), origin: 90_000, fail_line: false };
        let result = Client::expand1(nested_client).run1(
            &server::SAME_THREAD, nested, Stream::new(&self.log), false);
        self.call("nested-exit", self.origin);
        result.map_err(|_| ())
    }
    fn span_start(&mut self, span: u32) -> u32 { self.call("start", span); span }
    fn span_end(&mut self, span: u32) -> u32 { self.call("end", span); span + 1 }
    fn span_line(&mut self, span: u32) -> usize {
        self.call("line", span);
        if self.fail_line { panic!("server-sentinel"); }
        span as usize
    }
    unsupported! {
        fn track_env_var(var: &str, value: Option<&str>);
        fn track_path(path: &str);
        fn literal_from_str(s: &str) -> Result<bridge::Literal<u32, String>, String>;
        fn emit_diagnostic(diagnostic: bridge::Diagnostic<u32>);
        fn ts_is_empty(stream: &Stream) -> bool;
        fn ts_from_str(src: &str) -> Result<Stream, String>;
        fn ts_to_string(stream: &Stream) -> String;
        fn ts_from_token_tree(tree: bridge::TokenTree<Stream, u32, String>) -> Stream;
        fn ts_concat_trees(base: Option<Stream>, trees: Vec<bridge::TokenTree<Stream, u32, String>>) -> Stream;
        fn ts_concat_streams(base: Option<Stream>, streams: Vec<Stream>) -> Stream;
        fn ts_into_trees(stream: Stream) -> Vec<bridge::TokenTree<Stream, u32, String>>;
        fn span_debug(span: u32) -> String;
        fn span_parent(span: u32) -> Option<u32>;
        fn span_source(span: u32) -> u32;
        fn span_byte_range(span: u32) -> Range<usize>;
        fn span_column(span: u32) -> usize;
        fn span_file(span: u32) -> String;
        fn span_local_file(span: u32) -> Option<String>;
        fn span_join(span: u32, other: u32) -> Option<u32>;
        fn span_subspan(span: u32, start: Bound<usize>, end: Bound<usize>) -> Option<u32>;
        fn span_resolved_at(span: u32, at: u32) -> u32;
        fn span_source_text(span: u32) -> Option<String>;
        fn span_save_span(span: u32) -> usize;
        fn span_recover_proc_macro_span(id: usize) -> u32;
        fn symbol_normalize_and_validate_ident(string: &str) -> Result<String, ()>;
    }
}

// Function items are zero-sized: no captured fn pointer crosses Client's reifier.
macro_rules! run_client {
    ($f:path, $cross:expr, $fail:expr, $log:expr) => {{
        let log = &$log;
        Client::expand1($f).run1(
            &server::MaybeCrossThread { cross_thread: $cross },
            FixtureServer { log: log.clone(), origin: 1, fail_line: $fail },
            Stream::new(log), false)
    }};
}
fn roundtrip(input: TokenStream) -> TokenStream {
    let mut spans = Vec::new();
    let mut span = Span::call_site();
    for expected in 2..=1025 {
        span = span.end();
        assert_eq!(span.line(), expected);
        assert!(span.start().eq(&span));
        spans.push(span);
    }
    for (offset, span) in spans.iter().enumerate().rev() { assert_eq!(span.line(), offset + 2); }
    input
}
fn retain(input: TokenStream) -> TokenStream { SAVED.with(|s| s.set(Some(Span::call_site()))); input }
fn stale(input: TokenStream) -> TokenStream { SAVED.with(|s| s.get().unwrap().line()); input }
fn dropping(input: TokenStream) -> TokenStream {
    let first = input.clone(); let middle = input.clone(); let last = input.clone();
    drop(middle); std::mem::forget(first); std::mem::forget(last); input
}
fn nested_client(input: TokenStream) -> TokenStream {
    CLIENT_THREADS.lock().unwrap().push(("inner", std::thread::current().id()));
    assert_eq!(Span::call_site().line(), 90_000); input
}
fn outer_client(input: TokenStream) -> TokenStream {
    CLIENT_THREADS.lock().unwrap().push(("outer", std::thread::current().id()));
    let before = Span::call_site();
    let nested = input.expand_expr().unwrap(); drop(nested);
    assert_eq!(before.line(), 1); assert!(before.eq(&Span::call_site())); input
}
fn client_panic(_input: TokenStream) -> TokenStream { let _ = Span::call_site().line(); panic!("client-sentinel"); }
fn server_panic(input: TokenStream) -> TokenStream { let _ = Span::call_site().line(); input }

#[test]
fn span_transport_grows_and_reuses_handles_in_both_strategies() {
    let _guard = SERIAL.lock().unwrap();
    for cross in [false, true] {
        let log = Shared::default();
        drop(run_client!(roundtrip, cross, false, log).unwrap_or_else(|e| panic!("{:?}", e.as_str())));
        let log = log.lock().unwrap();
        assert_eq!(log.calls.iter().filter(|(name, _)| *name == "end").count(), 1024);
        assert_eq!(log.calls.iter().filter(|(name, _)| *name == "start").count(), 1024);
        assert_eq!(log.calls.iter().filter(|(name, _)| *name == "line").count(), 2048);
    }
}
#[test]
fn stale_same_thread_span_reaches_real_dispatcher_and_is_rejected() {
    let _guard = SERIAL.lock().unwrap(); let log = Shared::default();
    drop(run_client!(retain, false, false, log).unwrap_or_else(|e| panic!("{:?}", e.as_str())));
    let error = run_client!(stale, false, false, log).err().expect("stale span accepted");
    assert_eq!(error.as_str(), Some("use-after-free in `proc_macro` handle"));
    assert!(log.lock().unwrap().calls.is_empty(), "invalid handle reached Server");
    SAVED.with(|s| s.set(None));
    drop(run_client!(roundtrip, false, false, log).unwrap_or_else(|e| panic!("{:?}", e.as_str())));
}
#[test]
fn token_stream_drop_order_survives_span_store_change() {
    let _guard = SERIAL.lock().unwrap();
    for cross in [false, true] {
        let log = Shared::default();
        drop(run_client!(dropping, cross, false, log).unwrap_or_else(|e| panic!("{:?}", e.as_str())));
        assert_eq!(log.lock().unwrap().drops, [3, 2, 4, 1]);
    }
}
#[test]
fn nested_dispatch_and_both_panic_boundaries_restore_bridge_state() {
    let _guard = SERIAL.lock().unwrap();
    for cross in [false, true] {
        let log = Shared::default(); CLIENT_THREADS.lock().unwrap().clear();
        drop(run_client!(outer_client, cross, false, log).unwrap_or_else(|e| panic!("{:?}", e.as_str())));
        let threads = CLIENT_THREADS.lock().unwrap().clone();
        assert_eq!(threads.len(), 2); assert_eq!(threads[0].0, "outer"); assert_eq!(threads[1].0, "inner");
        assert_ne!(threads[0].1, threads[1].1, "nested client reentered outer TLS");
        assert_eq!(log.lock().unwrap().calls, [("nested-enter", 1), ("line", 90_000), ("nested-exit", 1), ("line", 1)]);
        assert_eq!(run_client!(client_panic, cross, false, log).err().unwrap().as_str(), Some("client-sentinel"));
        assert_eq!(run_client!(server_panic, cross, true, log).err().unwrap().as_str(), Some("server-sentinel"));
        drop(run_client!(roundtrip, cross, false, log).unwrap_or_else(|e| panic!("{:?}", e.as_str())));
    }
}
