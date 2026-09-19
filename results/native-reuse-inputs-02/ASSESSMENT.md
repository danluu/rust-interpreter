# Native reuse input stability

The offline census passes seven Rust controls in debug and release and four
Python controls. It validates54distinct retained artifacts (788MB), emits
194,171function identity records (65.7MB), and compares133chronological
transitions including95valid source edits. No guest, original project build,
native code publication or production runtime change occurred. Closure verifies
339frozen inputs,223source bindings and185evidence files against24540/24583.

| History | Valid edits | Edits changing the conservative namespace | Median unchanged bodies at the same ID |
| --- | ---: | ---: | ---: |
| fre token | 15 | 9 | 65.14% |
| fre folded | 15 | 12 | 68.70% |
| pgrust | 15 | 15 | 94.19% |
| rg-aot | 15 | 15 | 4.95% |
| Nushell types | 15 | 15 | 7.39% |
| Full parser | 15 | 9 | 99.95% |
| Recent token primary | 5 | 3 | 61.56% |

The median fraction preserving the complete conservative identity is zero in
every history. That identity includes all readonly data and static initializer
bytes, TLS declarations and the function count. Its failure does not prove
that all native bodies need recompilation: some inputs may belong to fresh
execution state rather than code emission. This is a useful rejection of a
coarse whole-program namespace as the sole cache partition, not a rejection
of more precise reuse. Numeric IDs and body contents also change substantially
in several histories; remapping cannot be assumed free or safe.

When the namespace does remain stable, unchanged caller bodies can still be
invalidated by direct callees. For example, token edits2and3 in the first cycle
preserve5,454local bodies, but only5,450complete input identities. The analogous
parser edits preserve11,831local bodies and11,830input identities. All original,
wrong-test and restoration transitions remain in the data.

Next review the adopted emitter's actual global dependencies, then use the
already saved identities to separate body/direct-callee stability from this
coarse namespace. Join exact original-artifact native maps only for an explicitly
scoped original-to-edited comparison. These are feasibility ceilings, not native
cache hits or hot-path savings. Keep scalar admission, code budgets, relocation
and assertion identities as unresolved implementation requirements.

The first attempt's invalid TLS fixture is separately closed. The validator
rejected reserved offset0; the corrected fixture uses16and independently checks
TLS declarations with unchanged backing bytes. No real artifact analysis from
the successful run needs to be repeated.
