# Real proc-macro client qualification

Attempt02 passed all 20 serial compiler commands: one stock and one candidate proc-macro dylib build, with nine identical caller cases per arm. The installed nightly compiler and its server remained unchanged. The candidate dylib used the separately built Arena04 client library and its matching literal dependency; saved dependency files and unchanged-input readback record that selection.

The cases cover exact emitted UTF-8 contents, identifiers and literals, oversized strings, compiler-scheduled nested expansions, diagnostics, panic recovery, stale-symbol rejection, and ordinary type/borrow errors. Default and explicitly selected same-thread cases are recorded separately; the default for these sources is already same-thread. This does not claim a cross-thread compiler test or simultaneous reentrancy.

The independent saved-file reader checked all 20 closures and raw diagnostics, stock/candidate diagnostic parity, dependency files, and 101 unchanged source/library/compiler inputs. All raw observations are retained here. Source-only labels in copied historical documents describe their original preparation moments.

Attempt01 remains failed: its first stock dylib compiled successfully, but the wrapper rejected an output-name warning caused by combining -o with multiple emit types. No later child ran. Attempt02 selected explicit emit paths and preserved the warning policy. Its separately reviewed 16 GiB entry reserve applies only to this fixed small fixture; installation/full-compiler policy remains 24 GiB.

This is functional qualification of an external proc-macro client with the existing compiler/server. It does not qualify a new compiler distribution, application workloads, performance, or a measured memory bound. The unchanged server's embedded rustc_proc_macro::quote client remains outside the Arena04 change. Recorded timestamps establish ordering and closure, not speed.

The capsule contains exact fixture sources/history, raw evidence for both attempts, owned output artifacts, and independent review sources/reports. Pre-existing client libraries and installed toolchain payloads are referenced by the retained input manifests and prior bridge qualification; they are not copied again. All original files remain unchanged.
