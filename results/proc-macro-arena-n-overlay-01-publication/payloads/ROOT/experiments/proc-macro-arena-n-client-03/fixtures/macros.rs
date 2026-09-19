//! Identical public-API proc-macro fixture for installed stock and Arena04.
//! No internal bridge/Arena API, filesystem/process access, or timing occurs.
extern crate proc_macro;

use proc_macro::{Delimiter, Group, Ident, Literal, Punct, Spacing, Span, TokenStream, TokenTree};
use std::cell::{Cell, RefCell};

const PAYLOAD: &str = "arena Ω\n\"\\🙂";
const REPR: &str = "\"arena Ω\\n\\\"\\\\🙂\"";
const LONG: usize = 8193;

thread_local! {
    // Only the dedicated same-thread callers use values across invocations.
    static STALE_IDENT: RefCell<Option<Ident>> = const { RefCell::new(None) };
    static STALE_LITERAL: RefCell<Option<Literal>> = const { RefCell::new(None) };
    static PANIC_REACHED: Cell<bool> = const { Cell::new(false) };
}

fn one_ident(input: TokenStream) -> Ident {
    let mut tokens = input.into_iter();
    let Some(TokenTree::Ident(ident)) = tokens.next() else { panic!("expected one fixture identifier") };
    assert!(tokens.next().is_none());
    ident
}

fn empty(input: TokenStream) {
    assert!(input.is_empty());
}

fn location(span: Span) -> (usize, usize, usize, usize) {
    (span.start().line(), span.start().column(), span.end().line(), span.end().column())
}

fn set_spans(stream: TokenStream, span: Span) -> TokenStream {
    stream.into_iter().map(|mut token| {
        if let TokenTree::Group(group) = token {
            token = TokenTree::Group(Group::new(group.delimiter(), set_spans(group.stream(), span)));
        }
        token.set_span(span);
        token
    }).collect()
}

fn exercise_symbols(span: Span) {
    let original_location = location(span);
    assert!(original_location.0 > 0 && original_location.1 > 0);
    assert_eq!(location(span.located_at(span)), original_location);
    assert_eq!(location(span.resolved_at(Span::call_site())), original_location);
    assert!(!span.file().is_empty());

    let mut early = Ident::new("arena_early", Span::call_site());
    early.set_span(span);
    let raw = Ident::new_raw("type", span);
    let unicode = Ident::new("café", span);
    let mut literal = Literal::string(PAYLOAD);
    literal.set_span(span);
    let mut kept = Vec::new();
    for index in 0..96 {
        let name = format!("arena_{index:03}_abcdefghijklmnopqrstuvwxyz");
        let value = format!("literal-{index:03}-abcdefghijklmnopqrstuvwxyz");
        kept.push((Ident::new(&name, span), Literal::string(&value), name, value));
    }

    // A request larger than one 4096-byte page, followed by another ordinary
    // symbol. All earlier public values remain live and are checked afterward.
    let long_name = "a".repeat(LONG);
    let long_ident = Ident::new(&long_name, span);
    let long_value = "z".repeat(LONG);
    let mut long_literal = Literal::string(&long_value);
    long_literal.set_span(span);
    let tail = Ident::new("arena_after_oversized", span);
    let long_stream: TokenStream = [TokenTree::Ident(long_ident.clone())].into_iter().collect();
    assert_eq!(long_stream.to_string(), long_name);
    let literal_stream: TokenStream = [TokenTree::Literal(long_literal.clone())].into_iter().collect();
    assert_eq!(literal_stream.to_string(), format!("\"{long_value}\""));
    let roundtrip: TokenStream = literal_stream.to_string().parse().unwrap();
    assert_eq!(roundtrip.to_string(), literal_stream.to_string());

    assert_eq!(early.to_string(), "arena_early");
    assert_eq!(raw.to_string(), "r#type");
    assert_eq!(unicode.to_string(), "café");
    assert_eq!(literal.to_string(), REPR);
    assert_eq!(long_ident.to_string().len(), LONG);
    assert_eq!(tail.to_string(), "arena_after_oversized");
    assert_eq!(location(early.span()), original_location);
    assert_eq!(location(literal.span()), original_location);
    assert_eq!(location(long_literal.span()), original_location);
    for (ident, literal, name, value) in kept {
        assert_eq!(ident.to_string(), name);
        assert_eq!(literal.to_string(), format!("\"{value}\""));
    }
}

fn expression(label: &Ident) -> TokenStream {
    let span = label.span();
    exercise_symbols(span);
    let values = [Literal::u64_suffixed(1337), Literal::string(PAYLOAD),
                  Literal::usize_suffixed(LONG), Literal::string(&label.to_string())];
    let mut inner = TokenStream::new();
    for mut value in values {
        value.set_span(span);
        inner.extend([TokenTree::Literal(value), TokenTree::Punct(Punct::new(',', Spacing::Alone))]);
    }
    let mut group = Group::new(Delimiter::Parenthesis, inner);
    group.set_span(span);
    TokenTree::Group(group).into()
}

#[proc_macro]
pub fn exercise(input: TokenStream) -> TokenStream {
    let ident = one_ident(input);
    // These callers supply real source identifiers, also retained by nest!.
    assert_eq!(ident.span().source_text().as_deref(), Some(ident.to_string().as_str()));
    expression(&ident)
}

#[proc_macro]
pub fn nest(input: TokenStream) -> TokenStream {
    let ident = one_ident(input);
    exercise_symbols(ident.span());
    let mut output: TokenStream = "arena04_macros::exercise!".parse().unwrap();
    output.extend([TokenTree::Group(Group::new(Delimiter::Parenthesis, TokenTree::Ident(ident).into()))]);
    output
}

#[proc_macro_attribute]
pub fn inspected(attr: TokenStream, item: TokenStream) -> TokenStream {
    empty(attr);
    exercise_symbols(Span::call_site());
    let copy = item.clone();
    assert_eq!(copy.to_string(), item.to_string());
    copy
}

#[proc_macro_derive(ArenaStamp)]
pub fn derive_stamp(input: TokenStream) -> TokenStream {
    let mut tokens = input.into_iter();
    // Derive input retains outer attributes; consume those real token groups
    // before the fixture's private unit struct, rather than assuming no attrs.
    loop {
        match tokens.next().unwrap() {
            TokenTree::Punct(punct) if punct.as_char() == '#' => {
                let TokenTree::Group(attr) = tokens.next().unwrap() else { panic!("expected attribute") };
                assert_eq!(attr.delimiter(), Delimiter::Bracket);
            }
            TokenTree::Ident(keyword) => { assert_eq!(keyword.to_string(), "struct"); break; }
            _ => panic!("expected fixture unit struct"),
        }
    }
    let TokenTree::Ident(name) = tokens.next().unwrap() else { panic!("expected struct name") };
    let TokenTree::Punct(end) = tokens.next().unwrap() else { panic!("expected unit struct end") };
    assert_eq!(end.as_char(), ';');
    assert!(tokens.next().is_none());
    exercise_symbols(name.span());
    set_spans(format!("impl {} {{ const ARENA_STAMP: usize = {LONG}; }}", name).parse().unwrap(), name.span())
}

#[proc_macro]
pub fn diagnose(input: TokenStream) -> TokenStream {
    let ident = one_ident(input);
    exercise_symbols(ident.span());
    set_spans("compile_error!(\"ARENA_FIXTURE_DIAGNOSTIC\");".parse().unwrap(), ident.span())
}

#[proc_macro]
pub fn deliberate_panic(input: TokenStream) -> TokenStream {
    empty(input);
    exercise_symbols(Span::call_site());
    PANIC_REACHED.set(true);
    panic!("ARENA_FIXTURE_PANIC");
}

#[proc_macro]
pub fn after_panic(input: TokenStream) -> TokenStream {
    empty(input);
    assert!(PANIC_REACHED.replace(false), "prior same-thread panic invocation was not observed");
    exercise_symbols(Span::call_site());
    // This exact error is evidence that the later callback completed after the
    // deliberate panic in this actual compiler process, not an ordering claim.
    "compile_error!(\"ARENA_FIXTURE_AFTER_PANIC\");".parse().unwrap()
}

#[proc_macro]
pub fn remember_ident(input: TokenStream) -> TokenStream {
    empty(input);
    exercise_symbols(Span::call_site());
    STALE_IDENT.with_borrow_mut(|slot| *slot = Some(Ident::new("remembered_ident", Span::call_site())));
    "arena04_macros::read_stale_ident!();".parse().unwrap()
}

#[proc_macro]
pub fn read_stale_ident(input: TokenStream) -> TokenStream {
    empty(input);
    let ident = STALE_IDENT.with_borrow_mut(|slot| slot.take()).expect("same-thread ident callback required");
    // Must be rejected by the real client's symbol invalidation boundary.
    let _ = ident.to_string();
    panic!("stale identifier unexpectedly survived");
}

#[proc_macro]
pub fn remember_literal(input: TokenStream) -> TokenStream {
    empty(input);
    exercise_symbols(Span::call_site());
    STALE_LITERAL.with_borrow_mut(|slot| *slot = Some(Literal::string("remembered_literal")));
    "arena04_macros::read_stale_literal!();".parse().unwrap()
}

#[proc_macro]
pub fn read_stale_literal(input: TokenStream) -> TokenStream {
    empty(input);
    let literal = STALE_LITERAL.with_borrow_mut(|slot| slot.take()).expect("same-thread literal callback required");
    let _ = literal.to_string();
    panic!("stale literal unexpectedly survived");
}

#[proc_macro]
pub fn mutate(input: TokenStream) -> TokenStream {
    let ident = one_ident(input);
    exercise_symbols(ident.span());
    set_spans(format!("{}.push('x')", ident).parse().unwrap(), ident.span())
}
