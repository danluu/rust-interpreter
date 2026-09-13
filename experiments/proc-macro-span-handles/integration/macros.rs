#![feature(proc_macro_span, proc_macro_expand, proc_macro_diagnostic)]
#![feature(proc_macro_tracked_env, proc_macro_tracked_path)]

extern crate proc_macro;
use proc_macro::{Literal, Span, TokenStream, TokenTree};
use std::io::Write;

// Exact source-edit anchor. Qualification changes 11 -> 19 -> 11.
const MACRO_OFFSET: u64 = 11;

fn record(id: &str, event: &str, value: &str) {
    let path = std::env::var("BRIDGE_LOG").expect("owned event log path");
    let mut file = std::fs::OpenOptions::new().create(true).append(true).open(path).unwrap();
    writeln!(file, "{id}\t{event}\t{value:?}").unwrap();
}
fn span_row(span: Span) -> String {
    format!("file={:?};local={:?};range={:?};line={};column={};end={}:{};text={:?}",
        span.file(), span.local_file(), span.byte_range(), span.line(), span.column(),
        span.end().line(), span.end().column(), span.source_text())
}
fn visit(id: &str, tokens: TokenStream, count: &mut usize) {
    for token in tokens {
        *count += 1;
        let span = token.span();
        let expected = span_row(span);
        // Every call goes through the real rustc server's span handle decoder.
        for _ in 0..8 { assert_eq!(span_row(span), expected); }
        assert!(span.eq(&span.resolved_at(span)));
        record(id, "span", &expected);
        if let TokenTree::Group(group) = token {
            record(id, "group-open", &span_row(group.span_open()));
            record(id, "group-close", &span_row(group.span_close()));
            visit(id, group.stream(), count);
        }
    }
}

#[proc_macro]
pub fn probe(input: TokenStream) -> TokenStream {
    let mut iter = input.into_iter();
    let id = match iter.next().unwrap() { TokenTree::Ident(id) => id.to_string(), _ => panic!("expected probe id") };
    record(&id, "begin", "probe");
    let env = proc_macro::tracked::env_var("BRIDGE_VALUE").expect("tracked input value");
    record(&id, "env", &env);
    let path = std::env::var("BRIDGE_DATA").expect("owned input path");
    proc_macro::tracked::path(&path);
    let bytes = std::fs::read_to_string(&path).unwrap();
    record(&id, "file", &bytes);
    let mut count = 0;
    visit(&id, iter.collect(), &mut count);
    record(&id, "tokens", &count.to_string());
    let result = env.parse::<u64>().unwrap() + bytes.trim().parse::<u64>().unwrap() + MACRO_OFFSET;
    record(&id, "end", &result.to_string());
    TokenTree::Literal(Literal::u64_suffixed(result)).into()
}

#[proc_macro]
pub fn inner(_: TokenStream) -> TokenStream {
    record("inner", "begin", "nested expansion");
    record("inner", "span", &span_row(Span::call_site()));
    record("inner", "end", "17");
    TokenTree::Literal(Literal::u64_suffixed(17)).into()
}

#[proc_macro]
pub fn nested(input: TokenStream) -> TokenStream {
    record("outer", "begin", "nested expansion");
    let saved = Span::call_site();
    let saved_row = span_row(saved);
    let ident = proc_macro::Ident::new("saved_identifier", saved);
    let literal = Literal::string("saved literal");
    let result = input.expand_expr().expect("nested literal expansion");
    assert_eq!(result.to_string(), "17u64");
    assert_eq!(span_row(saved), saved_row);
    assert_eq!(ident.to_string(), "saved_identifier");
    assert_eq!(literal.to_string(), "\"saved literal\"");
    record("outer", "span-after", &saved_row);
    record("outer", "end", "17");
    result
}

#[proc_macro]
pub fn warn(input: TokenStream) -> TokenStream {
    record("warning", "begin", "diagnostic");
    let span = input.into_iter().next().expect("diagnostic token").span();
    span.warning("bridge fixture warning").emit();
    record("warning", "end", &span_row(span));
    TokenStream::new()
}

#[proc_macro]
pub fn fail(input: TokenStream) -> TokenStream {
    record("failure", "begin", "diagnostic");
    let span = input.into_iter().next().expect("diagnostic token").span();
    span.error("bridge fixture explicit error").emit();
    record("failure", "end", &span_row(span));
    TokenStream::new()
}

#[proc_macro]
pub fn explode(input: TokenStream) -> TokenStream {
    record("panic", "begin", &span_row(input.into_iter().next().unwrap().span()));
    panic!("bridge fixture deliberate panic");
}
