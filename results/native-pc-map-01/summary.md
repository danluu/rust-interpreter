The diagnostic VM preserves every native word emitted by retained6bf on the original token and folded artifacts, including the profiled folded run. All172 existing bytecode tests pass, the full folded execution profile is unchanged, and each of six sampled runs passes its own clean-emitter comparison. Every sampled generated PC resolves to a native word, function and bytecode/exit interval. Original assertions and production RNG remain intact.

**folded**: 1,082 generated-code stacks out of 2,570 total main-thread stacks across three runs.

| Generated helper category | Samples | Share of generated |
|---|---:|---:|
| load_mem | 382 | 35.3% |
| other-native-instruction | 323 | 29.9% |
| register-store | 205 | 18.9% |
| store_mem | 86 | 7.9% |
| checked_address | 66 | 6.1% |
| register-load | 20 | 1.8% |

| Function | Samples | Share of generated |
|---|---:|---:|
| `folded_literal_trie::FoldedLiteralTriePlan::scan_upper_bounds[]` | 240 | 22.2% |
| `folded_literal_trie::tests::common_offset_prefilter_matches_scalar_reference_on_all_short_byte_strings_and_windows[]` | 167 | 15.4% |
| `folded_literal_trie::scan_folded_start[Closure(DefId(0:11968 ~ fre_kernels[f022]::folded_literal_trie::tests::common_offset_prefilter_matches_scalar_reference_on_all_short_byte_strings_and_windows#1::{closure#0}), [i16, Binder { value: extern "RustCall" fn((literal_anchor::LiteralCandidate,)), bound_vars: [] }, (&'{erased} mut std::vec::Vec<literal_anchor::LiteralCandidate, std::alloc::Global>,)])]` | 146 | 13.5% |
| `folded_literal_trie::execute_folded_scan_impl[Closure(DefId(0:11968 ~ fre_kernels[f022]::folded_literal_trie::tests::common_offset_prefilter_matches_scalar_reference_on_all_short_byte_strings_and_windows#1::{closure#0}), [i16, Binder { value: extern "RustCall" fn((literal_anchor::LiteralCandidate,)), bound_vars: [] }, (&'{erased} mut std::vec::Vec<literal_anchor::LiteralCandidate, std::alloc::Global>,)])]` | 109 | 10.1% |
| `folded_literal_trie::RootPrefilter::scan[Closure(DefId(0:11969 ~ fre_kernels[f022]::folded_literal_trie::tests::common_offset_prefilter_matches_scalar_reference_on_all_short_byte_strings_and_windows#1::{closure#1}), [i16, Binder { value: extern "RustCall" fn((literal_anchor::LiteralCandidate,)), bound_vars: [] }, (&'{erased} mut std::vec::Vec<literal_anchor::LiteralCandidate, std::alloc::Global>,)])]` | 98 | 9.1% |
| `folded_literal_trie::execute_folded_scan_impl[Closure(DefId(0:11969 ~ fre_kernels[f022]::folded_literal_trie::tests::common_offset_prefilter_matches_scalar_reference_on_all_short_byte_strings_and_windows#1::{closure#1}), [i16, Binder { value: extern "RustCall" fn((literal_anchor::LiteralCandidate,)), bound_vars: [] }, (&'{erased} mut std::vec::Vec<literal_anchor::LiteralCandidate, std::alloc::Global>,)])]` | 70 | 6.5% |
| `folded_literal_trie::decode_scalar[]` | 54 | 5.0% |
| `folded_literal_trie::checked_actual_add[]` | 53 | 4.9% |

**token-phrase**: 3,030 generated-code stacks out of 7,689 total main-thread stacks across three runs.

| Generated helper category | Samples | Share of generated |
|---|---:|---:|
| other-native-instruction | 950 | 31.4% |
| load_mem | 869 | 28.7% |
| register-store | 705 | 23.3% |
| checked_address | 236 | 7.8% |
| store_mem | 216 | 7.1% |
| register-load | 54 | 1.8% |

| Function | Samples | Share of generated |
|---|---:|---:|
| `std::ptr::copy_nonoverlapping::precondition_check[]` | 449 | 14.8% |
| `token_phrase::enforce_upper_bounds[]` | 314 | 10.4% |
| `token_phrase::TokenPhrasePlan::scan_block_masks[]` | 182 | 6.0% |
| `core::slice::sort::stable::quicksort::PartitionState::<T>::partition_one[std::vec::Vec<u8, std::alloc::Global>]` | 156 | 5.1% |
| `core::slice::sort::stable::quicksort::stable_partition[std::vec::Vec<u8, std::alloc::Global>, FnDef(DefId(2:30283 ~ core[affe]::cmp::PartialOrd::lt), Binder { value: [std::vec::Vec<u8, std::alloc::Global>, std::vec::Vec<u8, std::alloc::Global>], bound_vars: [] })]` | 143 | 4.7% |
| `<A as core::slice::cmp::SliceOrd>::compare[u8]` | 136 | 4.5% |
| `token_phrase::verify[usize, usize]` | 134 | 4.4% |
| `token_phrase::TokenPhrasePlan::consume_classified_block[]` | 121 | 4.0% |

These are diagnostic distributions, not timing comparisons or predicted savings. Phase, helper and opcode tables each classify the same samples. The host binary differs; cold compilation includes metadata collection. Only outer function paths containing `::tests::` or `::test::` are labeled as test paths; generic arguments containing a test closure do not relabel a production function. PC samples do not measure individual instruction latency or prove the source of a hardware stall. No engine optimization has been integrated.
