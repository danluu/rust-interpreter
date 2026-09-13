# Wide bitwise and shift operations

The current integrated-VM census finds4,842,143 interpreted binary operations
in the original token block-boundary test:2,421,047128-bit Shl,2,304,975 And,
116,119 Or and two Shr operations. That accounts for71.5% of its interpreted
operations, not71.5% of elapsed time. The exhaustive test has only18,823 such
operations and remains part of the complete twelve-test comparison.

Extend the typed AArch64 emitter for128-bit And/Or/Xor/Shl/Shr. Keep two64-bit
words, capture inputs before writes, preserve value-then-overflow assignment
order and the existing false overflow result for bitwise/shift operations.
Shift counts wrap modulo128. Handle zero and64 separately from hardware's
modulo64 variable shifts; signed right shifts retain sign extension.
No host arithmetic callback, LLVM guest code, memory-model change, artifact
rewrite or relaxed checking is involved.

Start from the exact qualified integrated runtime241ac6e/VM49746a22, removing
the separately parked capacity-credit implementation. Retain its exporter and
wrapper bytes. Expand the independent native Rust oracle across all shift
residues, high count words, signedness, aliased operands/results and far slots.
Add a nested-call/profile test covering every budget tail, native declines,
persistent registers and resumable execution. Existing generated CFG, TLS,
memory and ABI qualification stays enabled.

Run all419 workspace tests in debug and release, one ignored, with two Cargo
workers and locked offline dependencies. Host qualification floor: 4 GiB.
Reuse the existing qualified host cache at
`.work/fixed-frame-clear-combined-build-01/target`; do not delete that cache.
Acquire the shared benchmark lock for at most45s and preserve exact owned
child identities. Freeze source before each build; stop on unexpected failure.

After host qualification, run the seven exact original saved selections,
nine serial/prepared-suite commands and203 strict native/cache checks. Include
the current three-test entropy-controlled profile pair to establish which VM
returns were removed while retaining exact logical outcomes. This is a
mechanism diagnostic, not a performance claim.

Then freeze one full token/folded/pgrust changed-source comparison: fifteen
edited pairs and fifteen A/A pairs per case, all original assertions, wrong
edits and compiled restoration. Keep two Cargo workers on every route, two
prepared custom workers, ordinary native libtest and line-tables controls.
The component gain must exceed same-session A/A, CPU must not increase, and
held-outs retain their5% guards. Preserve the composed8% target against the
fixed selected-suite anchor, all outcomes and noise bounds. No partial-pair
selection, retiming of this candidate or unchanged-build claim. Source remains
experimental until qualified and measured.
