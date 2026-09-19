extern crate proc_macro;

#[proc_macro]
pub fn host_debug_assertions(_: proc_macro::TokenStream) -> proc_macro::TokenStream {
    cfg!(debug_assertions).to_string().parse().unwrap()
}
