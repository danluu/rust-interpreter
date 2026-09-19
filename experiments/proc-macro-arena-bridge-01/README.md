# Standalone proc-macro library bridge and symbol lifecycle fixture

This is an uncompiled, unrun fixture for the real public `proc_macro` library's
`Client`, `Dispatcher`, handle stores and symbol interner. It uses the existing
concrete `FixtureServer` implementation and real library objects. It contains
no replacement Arena, Interner or transport model. It is not a rustc-server,
macro-dylib/caller, compiler-distribution or performance qualification.

`original/bridge.rs` is an exact copy of the existing span-handles integration
fixture. The four stock test functions and their exact span, RPC, destructor,
nested-thread and panic assertions remain byte-identical. The sole existing
server change calls a symbol-bearing wrapper around the original nested client.
That wrapper preserves the original span RPC and thread observations. Every
unsupported server method still panics; no no-op success or fabricated general
identifier-normalization implementation is added.

Four new tests exercise actual nonempty symbol storage. Repeated calls verify
small and duplicate ASCII identifiers, raw identifiers, Unicode and escaped
literals, and an 8193-byte ASCII identifier while earlier values remain live.
They assert exact server calls, stream destruction and thread identities.
Same-thread calls reuse the client TLS; cross-thread calls exercise fresh client
threads and do not claim cross-call arena reuse. A second test retains an Ident
and a Literal across completed same-thread invocations and requires the exact
stale-symbol rejection before any server call, followed by successful reuse.
A third holds outer and inner symbols across nested dispatch, checks their
contents and exact event/thread/RPC/destruction order. A fourth requires exact
client/server panic messages after nonempty intern activity and successful
subsequent calls, with exact event and drop counts.

Unicode goes through the actual `Literal::string` escaping and interning path;
only valid ASCII identifiers use the library's local identifier-validation
path. This does not test rustc's Unicode identifier normalization. The 8193-byte
value exercises large symbol storage; public behavior cannot directly prove
page retention, which remains covered by the separate actual Arena tests.
The new symbol constructors and conversions all execute inside `Client::run1`.

A future run must build the full actual proc-macro library from the root's
identified eighteen-source closure with only the selected Arena/symbol changes,
using the matching installed nightly and the already rebuilt real literal
dependency. It must compile this fixture with an explicit
`--extern proc_macro=ABSOLUTE_NEW_RLIB` and `-L dependency=OWNED_LIBRARY_DIRECTORY`,
then run all eight tests together with `--test-threads=1`. Preserve the exact
library, dependency, compiler, standard-library, source, command and raw result
identities. Do not copy a library into an existing installation or infer its
identity from a toolchain alias. This standalone test does not require a full
compiler build and cannot claim to qualify that compiler's internal server.

Keep the canonical workload lock across the finite library/fixture builds and
test run, with the already reviewed bounded child-closure pattern. A proposed
small-run bound is CPU 120 seconds and wall 180 seconds per library or fixture
compile, CPU 30 seconds and wall 60 seconds for the tests, 64 MiB per output file
and 128 MiB total retained output. Admission thresholds remain the parent run's
explicit policy; this source fixture neither lowers a gate nor starts work.
Expected panics stay in the saved raw output. No test-name filter, retry,
benchmark, sysroot mutation or installed-component change is authorized here.
