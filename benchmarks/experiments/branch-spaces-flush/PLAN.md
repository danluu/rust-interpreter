# Branch-selected fixed addresses with successor-only flushing

Base a72daa14 retains adopted production emission. The exact small-memory
diagnostic attributes188/1651 and66/1439 generated samples to arena selection,
versus65/18 to range checks. This motivates a different selector, not a latency
prediction or a repeat of the rejected CCMP range rewrite. The standalone
successor-flush full primary failed its gate despite a3.25% observed gain; retain
it only as a separately qualified component of this new composition.

For fixed-size checked addresses, branch on address>>62 to select exactly the
same unsigned address>=1<<62 rule. Select only one backing base and length;
select a readonly boundary only for writes. Subtract the full tag on the heap
path, including malformed addresses above2*TAG. Never test only bit62. Preserve
all existing complete bounds/null/readonly checks, zero-size bypasses, source-
before-destination and all-before-write rules, dynamic-address emission, scratch
and persistent registers, logical budgets, ABI, layouts and16MiB code capacity.
This also qualifies fixed checks in native call/return and range-guard paths.

The selector grows from8 static words to9(read)/11(write). Executed paths use
4/5 linear words or7/8 heap words. Extra branches and code footprint may erase
the benefit. No size or speed outcome is assumed. Ordinary regions with full
CFG liveness additionally omit only successor-dead array spills; native-call
trees retain their previous tail contract. No frontend/checking policy changes.

Normal tests exercise the candidate. Test-only historical switches reconstruct
the adopted emitter for exact saved-capture checks. Verify the actual selector
against unsigned Rust arithmetic for both upper bits, boundaries and deterministic
mixed addresses, with live-register/ABI controls. Retain full-range copy/fault
tests and every-budget, profiling, capacity, persistent-register and call-mode
tests. Verify instruction encodings against local assembler-only controls.

Qualify debug/release workspace tests, install only a composed VM with retained
35df4077 compiler/wrapper binaries, then run strict/cache controls, exact workload
profiles and offline full-function reconstruction before the40-command changed-
source primary screen. Screen failure stops this candidate. Passing permits a
fresh full five-project history and complete parser qualification; it does not
authorize adoption by itself. Preserve native/A/A/anchor controls, valid/wrong/
restored production edits, original assertions and source/artifact identities.

Use the shared benchmark lock,45-second admission, two Cargo workers,16GiB build
admission and8GiB child floors. Admit larger stages separately with current disk
evidence. Preserve peers, all completed receipts, suggestions.txt and the paused
goal. No third-party guest backend, subagent, AWS activation or peer control.
