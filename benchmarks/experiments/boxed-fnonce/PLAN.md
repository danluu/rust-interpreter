# By-value dynamic receivers

The original gram_core native target passes114 tests. Exporting the exact same
set fails in std's Box<F, A>::call_once before guest execution. The pinned
alloc/src/boxed.rs:2366 forwards `FnOnce::call_once(*self, args)`. The exporter
already carries metadata on an unsized dereferenced Location, but virtual_call
unconditionally uses call_arguments and requires a16-byte stored receiver.

First qualify an independent original native fixture and retain the existing
exporter's expected failure. Add only the general dynamic by-value receiver
path: use that place's data address and vtable metadata, transfer the data
pointer to the vtable shim, and preserve ordinary argument flattening. Reject
other unsized receiver kinds. Sized virtual receivers retain their old path.
No guest engine changes, LLVM guest fallback, checking bypass or fake callback.

Fixture coverage: owned non-Copy captures, empty/ZST closures, RustCall tuple
arguments including ZST and u128, aggregate return, aligned captured data,
borrowed lifetimes, nested boxed closures, callback vectors and exactly-once
destruction. Native libtest retains default threading. Custom execution uses
fresh guest state per test. Do not claim unwind support from successful calls.

Use the shared45-second benchmark admission, two Cargo jobs, initial12GiB and
per-command8GiB floors. Freeze source/helper/tool inputs, record commands and
terminal outcomes. Before: one full native command and one old custom export,
which must fail with the observed diagnostic and produce no guest report.
After: unchanged complete fixture under custom interpreter, ordinary JIT and
resumable/persistent JIT; native proof is reused only after byte/hash validation.
Check the exporter in debug/release and retain the exact already-qualified VM.
Broaden to existing dynamic/closure fixtures and strict uncalled type/borrow
failures after the targeted regression passes. Then try the complete original
parser test set again with the qualified tool. No performance claim or timing
gate changes arise from this support fix.
