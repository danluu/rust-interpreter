use proc_macro::TokenStream;

#[proc_macro]
pub fn offset(_: TokenStream) -> TokenStream {
    format!("{}u64", host_mir_shared::shared_value(2)).parse().unwrap()
}
