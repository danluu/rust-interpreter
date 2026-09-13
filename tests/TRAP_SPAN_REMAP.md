These are source-only regression controls for the two runtime `Op::Trap`
location strings in `crates/mir-export/src/lower.rs`. They have not been built
or executed. They change no exporter, VM, compiler, benchmark, or source-map
policy. The caller must serialize every build/run under
`/Users/danluu/dev/rust-interp/.work/benchmark.lock` and retain the outer process
receipt. The tests never acquire a nested lock or build tools themselves.

The reviewed fix replaces only those two uses of
`span_to_diagnostic_string(span.source_callsite())` with
`span_to_string(span.source_callsite(), RemapPathScopeComponents::MACRO)`.
For the exact pinned compiler (public `cea272fa356e94bd2ee2cadf376630aa0683867a`,
owned production `58e1e1f5311f4424ea81def4763081f6da62d9b3`):

- `compiler/rustc_span/src/source_map.rs:511` explicitly forbids embedding
  diagnostic-format spans in build artifacts. Its old
  `span_to_embeddable_string` cross-reference is stale; the current explicit
  interface is `span_to_string` at line 466.
- `compiler/rustc_middle/src/mir/consts.rs:532` implements native
  `span_as_caller_location` using `FileName::display(MACRO)`.
- `compiler/rustc_builtin_macros/src/source_util.rs:61` implements `file!()`
  using the same filename scope.
- The change preserves the existing `source_callsite()` traversal and range
  formatting. It does not claim that all native caller-location columns and
  source-map columns are equivalent: native uses display columns; the existing
  trap range uses character columns. The fixture uses ASCII and no tabs.

`trap_span_remap_fixture.rs` contains a macro-generated direct panic and a
direct panic preceded by a projected write. At `mir-opt-level=0`, the first
panic block must have only preparation statements; the second must contain
`(*_1) = const 29_u64` in the panic's own block. The test checks the actual
export-time optimized MIR dumps, the first exported function's sole Trap,
and the second function's surviving Store before its Trap. If the pinned MIR
or lowering shape changes, these coverage assertions fail rather than silently
claiming both paths were exercised. Native panic recovery also checks that the
write really happened.

The first ignored Rust test uses identical source copies in two owned absolute
roots and no mapping, macro-only, diagnostics-only, and all remap scopes. It
deserializes and validates each real RBC, executes the supplied actual VM,
checks both trap messages exactly against native panic locations, and retains
actual native `file!()`/caller-location bytes. The VM comparison of the existing
64-bit numeric file/caller encoding is a supplemental check, not proof of exact
guest string equality (hash collisions are possible). Full guest file/caller
string/coordinate equivalence remains the separately required 61-command
source-observable qualification. This regression proves exact Trap filename
scope and complete artifact equality without weakening that prerequisite.
It compares complete, unmodified bytecode bytes:

- Within one root: no mapping equals diagnostics-only; macro-only equals all.
- Across roots: macro-only/all artifacts agree; no mapping/diagnostics-only
  artifacts differ because the file and caller observables really differ.

The second test injects unused type, borrow, and constant errors for each scope.
Native rustc and the exporter receive the same source/sysroot/checking flags.
Their entire diagnostic JSON records must agree, including rendered text,
children, suggestions, spans and snippets. Every error is followed by an
ordinary successful native check, strict export and execution of restored
source. Failed exports must leave no runnable artifact. There is no diagnostic
or artifact string rewriting, and no unchecked-analysis mode.

After the runtime fix and exact matching tools are built, provide absolute
`RUST_INTERP_TEST_EXPORTER`, `RUST_INTERP_TEST_RUSTC`, `RUST_INTERP_TEST_VM`,
`RUST_INTERP_TEST_STD_SYSROOT`, and an existing fresh parent directory in
`RUST_INTERP_TEST_ARTIFACT_DIR`. The supplied std sysroot supplies metadata/MIR
needed by the same compiler; native linked binaries use the physical compiler's
own native sysroot. Native metadata-only diagnostic checks and exports use the
same prepared std sysroot, so raw diagnostic comparison does not cross differing
std source maps. Use the already-qualified prepared sysroot, not a new
preparation during this test. The exporter capability
must name the exact selected compiler's physical sysroot. With the canonical
lock held, build/run only the `rust-interp-bytecode` integration target
`trap_span_remap` using the repository's normal locked/offline build profile,
at most two jobs, and `-- --ignored --test-threads=1`. An exact pre-fix exporter
can be a negative control in a separate fresh retained directory; failure
there is expected and must remain labeled as such.

The two tests respectively issue 67 and 63 bounded compiler/runtime/probe
commands, all serial. Each command retains PID, parent PID, argv, cwd, times,
status, raw stdout/stderr and actual source bytes/hash. Tool binaries and
test/fixture sources are hashed and guarded. All raw native outputs, MIR dumps
and bytecode files remain in the requested directory. Parent qualification
retains the already-verified full tool/std identities and outer lock receipt;
these focused tests do not publish or replace those identities. They establish
scope correctness only, with no timing or speed claim.
