use proc_macro::TokenStream;

/// Compile-time execution remains native in both proposed routes.
#[proc_macro]
pub fn fixture_value(input: TokenStream) -> TokenStream {
    let value: u64 = input.to_string().parse().expect("one unsigned integer literal");
    #[cfg(feature = "shared-helper")]
    let value = ibs_fixture_helper::transform(value, 0);
    format!("{value}u64").parse().unwrap()
}
