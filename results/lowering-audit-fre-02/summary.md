# Test-body lowering audit: fre / fre-kernels

79 of 389 selected bodies lowered; 310 were blocked. The native binary listed 389 test bodies. Ordinary frontend checking ran. No test body was executed. Lowering success does not establish test success, custom-harness compatibility, or complete application support. Each blocked body records the first encountered blocker, not every missing capability.

| First lowering blocker | Bodies |
|---|---:|
| unsupported intrinsic caller_location | 142 |
| unsupported intrinsic ptr_mask | 25 |
| unsupported rvalue &/*tls*/ forward_anchored::exact_suffix_copy_probe::FAILURE::{constant#0}::{closure#1}::__RUST_STD_INTERNAL_VAL | 19 |
| unsupported target intrinsic llvm.aarch64.neon.tbl1.v16i8 | 12 |
| unsupported rvalue &/*tls*/ forward_anchored::exact_suffix_copy_probe::CALLS::{constant#0}::{closure#1}::__RUST_STD_INTERNAL_VAL | 11 |
| unsupported dynamic layout for alloc::sync::ArcInner<str> | 8 |
| unsupported rvalue &/*tls*/ ordered_literal_aggregate::build_allocation_probe::CALLS::{constant#0}::{closure#1}::__RUST_STD_INTERNAL_VAL | 8 |
| unsupported rvalue &/*tls*/ folded_literal_trie::build_probe::SCALAR_READS::{constant#0}::{closure#1}::__RUST_STD_INTERNAL_VAL | 7 |
| unsupported rvalue &/*tls*/ folded_literal_trie::build_probe::ALLOCATION_ATTEMPTS::{constant#0}::{closure#1}::__RUST_STD_INTERNAL_VAL | 7 |
| unsupported rvalue &/*tls*/ forward_anchored::EDGE_WITNESS_VISITS::{constant#0}::{closure#0}::__RUST_STD_INTERNAL_VAL | 7 |
| unsupported rvalue &/*tls*/ ordered_literal_aggregate::build_allocation_probe::FAIL_AT::{constant#0}::{closure#1}::__RUST_STD_INTERNAL_VAL | 7 |
| MIR unavailable for libc::unix::bsd::apple::clock_gettime | 6 |
| unsupported rvalue &/*tls*/ prefix_class_alternation::uniform_scan_fault::AFTER_RESULT::{constant#0}::{closure#1}::__RUST_STD_INTERNAL_VAL | 6 |
| unsupported rvalue &/*tls*/ sparse_ordered_literal_aggregate::build_allocation_probe::FAIL_AT::{constant#0}::{closure#1}::__RUST_STD_INTERNAL_VAL | 5 |
| unsupported rvalue &/*tls*/ url_aggregate::allocation_probe::BUILD::{constant#0}::{closure#1}::__RUST_STD_INTERNAL_VAL | 5 |
| unsupported rvalue &/*tls*/ fixed_absolute_domain::exact_allocation_probe::CALLS::{constant#0}::{closure#1}::__RUST_STD_INTERNAL_VAL | 4 |
| unsupported rvalue &/*tls*/ folded_literal_trie::scan_source_probe::ACCESSES::{constant#0}::{closure#1}::__RUST_STD_INTERNAL_VAL | 4 |
| unsupported rvalue &/*tls*/ sparse_ordered_literal_aggregate::build_allocation_probe::CALLS::{constant#0}::{closure#1}::__RUST_STD_INTERNAL_VAL | 4 |
| unsupported rvalue &/*tls*/ byte_candidate_stream::scan_source_probe::ACCESSES::{constant#0}::{closure#1}::__RUST_STD_INTERNAL_VAL | 3 |
| unsupported rvalue &/*tls*/ byte_candidate_stream::build_probe::SOURCE_READS::{constant#0}::{closure#1}::__RUST_STD_INTERNAL_VAL | 3 |
| unsupported rvalue &/*tls*/ fixed_absolute_domain::exact_allocation_probe::FAILURE::{constant#0}::{closure#1}::__RUST_STD_INTERNAL_VAL | 3 |
| unsupported rvalue &/*tls*/ regex_automata::util::pool::inner::THREAD_ID::{constant#0}::{closure#1}::__RUST_STD_INTERNAL_VAL | 3 |
| unsupported rvalue &/*tls*/ byte_candidate_stream::build_probe::ALLOCATION_ATTEMPTS::{constant#0}::{closure#1}::__RUST_STD_INTERNAL_VAL | 2 |
| unsupported rvalue &/*tls*/ packed_ordered_literal_aggregate::build_allocation_probe::FAIL_NEXT::{constant#0}::{closure#1}::__RUST_STD_INTERNAL_VAL | 2 |
| unsupported rvalue &/*tls*/ exact_literal_copy_probe::CALLS::{constant#0}::{closure#1}::__RUST_STD_INTERNAL_VAL | 2 |
| unsupported rvalue &/*tls*/ url_aggregate::allocation_probe::REDUCE::{constant#0}::{closure#1}::__RUST_STD_INTERNAL_VAL | 2 |
| unsupported cast PointerCoercion(ClosureFnPointer(Safe), Implicit) | 1 |
| unsupported rvalue &/*tls*/ exact_literal_copy_probe::FAILURE::{constant#0}::{closure#1}::__RUST_STD_INTERNAL_VAL | 1 |
| MIR unavailable for libc::unix::fstat | 1 |
