#[proc_macro]
pub fn value(_: proc_macro::TokenStream) -> proc_macro::TokenStream {
    format!("const MACRO_VALUE: u64 = {};", worker_shared::value()).parse().unwrap()
}
