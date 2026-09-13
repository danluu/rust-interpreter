# General boxed FnOnce support

The exporter now lowers a by-value dynamic receiver using its place's data
address and vtable metadata. This is how the pinned standard library forwards
`Box<dyn FnOnce>::call_once`. The concrete vtable shim receives a thin pointer;
ordinary MIR retains capture moves, destruction and Box deallocation. Sized
virtual receivers retain their original path. Type and borrow checking remain
strict, with no alternate guest backend or project-specific callback shim.

Six native tests pass. The old exporter reproduces the original parser failure.
The new tool passes all six in the interpreter, ordinary JIT and resumable JIT
(18 guest test executions in13 commands). Tests cover owned and borrowed
captures, ZST environments/arguments, wide tuples and aggregate results,
alignment, nested callbacks, callback vectors and exactly-once destruction.
This does not establish panic-unwind support.

Both exporter test profiles pass88 tests. Another78 commands verify existing
dynamic/closure fixtures against native across three inputs, cold/warm/off
function caches, Cargo helper edits/restoration, and rejection of uncalled
type/borrow errors with incremental compilation both enabled and disabled.
The sized dynamic fixture's bytecode is identical to the adopted control.
All build/qualification frozen inputs and12 exact selected-test identities
verify in the final audit, with no repeated guest command.

Tool `155749049862e62c766aff170d37d75a448d6220c5ed174066c400e26e511604`
retains VM `4e9c9af6` and wrapper `10fb7656`. Only the exporter changes.
The original fixture syntax error and driver-flag rejection remain recorded;
the six successful native tests were reused after validation.

The complete original114-test pgrust parser selection now gets past the boxed
callback, then reaches the existing10,000-function expansion limit. It still
does not execute guest tests. Preserve that limitation and diagnose graph
growth before changing admission limits. These are support/correctness results,
not an edited-command speedup or a replacement for the five performance guards.
