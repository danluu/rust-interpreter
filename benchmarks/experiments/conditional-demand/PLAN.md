# Conditional demand preparation

The broad demand candidate is parked after its complete failed token primary.
The closed current-parser diagnostic motivates an independent structural policy:
`--jit-demand-regions-if-large` enables demand preparation across the immutable
program if any function exceeds the existing 65,536-PC CFG-analysis bound.
Programs at or below the bound use eager preparation; the effective owner mode
controls the VM loop. Unreachable large functions deliberately count. No names,
project IDs or selected-test identities influence this decision.

Both demand policies require full validation and resumable JIT even when the
conditional predicate is false. They are mutually exclusive. Prepared owners
freeze the requested policy. Code, retained plans and publication metadata keep
the existing independent 16 MiB bounds. No lazy type or borrow checking.

Build qualification uses the existing shared ROOT target, two Cargo workers, two Rust test
workers, full debug and release workspace checks (640 passed, 15 ignored each),
431 Python controls (409 passed, 22 skipped), release VM packaging with the exact
adopted compiler and both exact eager-code captures. Boundaries 65,536/65,537,
unused large functions, ordinary execution, prepared reuse/faults and full
validation are controlled. Build admission is max(14 GiB, 8 GiB plus twice the
allocated shared target); each child retains the 8 GiB floor. Source, commands,
logs, tool hashes and terminal state must close before claiming qualification.

Build 01 stopped on a diagnostic-specific test assertion, corrected in build 02.
Build 02 passed all debug controls, then stopped on its disk reservation before
release. Build 03 binds and reuses that exact debug command with matching frozen
runtime, tests, launcher and build inputs; it runs the remaining five commands.
Both retained and new setup time are reported, and the failed runs stay closed.

Next qualify the complete strict/cache workflow and unchanged original logical
profiles. Small-program operation maps must remain eager schema 2. A fresh
parser profile must select demand schema 3 and preserve exact counts, memory,
entropy and native-map reconstruction. Then preregister a parser-primary
changed-source comparison with adopted duplicate/native/anchor arms, five edit
pairs, and the existing A/A/noise gate. Passing that screen permits fuller parser
histories and token/folded/pgrust/rg-aot/Nushell regression guards. No latency gain
or adoption is implied by coverage or code-size improvements. Frozen failed
broad-candidate measurements stay failed; no selective retiming.
