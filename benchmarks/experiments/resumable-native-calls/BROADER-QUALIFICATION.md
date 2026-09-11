# Broader experimental execution qualification

The two fixed-tool E2E runs improve folded 19.51%/19.15% and token 19.95%/19.97%.
Both narrowly fail token's original 20% numerical gate. Those failures stay
recorded. Next characterize broader compatibility on the experimental candidate:
that is more useful than further attempts at crossing this fine cutoff or
another batch-size tweak. This is not retention, a default change or a waiver
of the original criteria. None of this document transfers older coverage.
Native/FFI fallback and success-returning OS/unwind shims remain out of scope.

The archived full validator driver hardcodes the old tool and JIT mode. Its
tracked replacement is `scripts/qualify_native_execution.py`. It accepts an
immutable tool key and explicit runtime flags, takes the benchmark lock, freezes
source/fixture/tool hashes and runs the existing full validator twice (default
and leaf inlining). Staging changes only root/tool/output paths and inserts flags
into JIT commands. Every existing assertion AST must remain identical. Python
assertions cannot be disabled. The staged source, substitutions, full commands,
outputs, process receipts and file hashes remain in the unique run directory.

`check_execution_driver.py` has verified staging for baseline,
resumable and tree/stub modes, reproduce both historical VM command counts and
rejects falsely labelled resumable commands. This is helper qualification only.
The actual full run then verifies every VM command uses the selected binary and
exact mode options, and requires successful native Call/Return counters when
resumable mode is selected. Code size and declined executions are reported.

The expected count is 23,502 mixed commands per mode: 11,119 interpreter and
11,119 JIT invocations, one default-engine rejection, 204 exports, 118 builds
and 941 native executions. Some native executions emit many oracle values.
These are command categories, not 23,502 distinct cases. Rejection checks and
partial-checking option tests remain unchanged; partial checking is not enabled
for the production development workflow. See the historical count correction.

After full native differential qualification, run the separate 245-command
TLS/destructor suite with the same selected runtime flags and real native
controls. The tracked `scripts/validate_tls_destructors.py` now selects the tool and mode
explicitly. Its complete case-generation AST matches the archived driver. It
preserves original assertions, three MIR settings, both inlining
settings, exact destructor order, all test resets, normal callback behavior,
terminal actual-panic failure and strict rejection controls. Do not claim full
unwinding merely because normal callbacks run.

Then recollect/replay the same 389 original fre bodies (382 previous passes,
seven ignored), with fresh native controls and the documented 150,000 allocation
limit, unsupported-call trapping and normal try callbacks. Flag every unsupported
or failed execution explicitly. A lowered audit body is not a passed test; this
remains body replay, not unfiltered libtest. The replay driver now carries explicit runtime modes and an optional allocation
limit. Nine coverage-driver CLI checks and the preserved TLS case matrix pass;
actual new-tool execution is still required.

Run all seven held-out real-edit workflows with the same original b2 baseline,
three cycles, flags, source pins, wrong edits, identical paired artifacts,
independent check references and restoration rules. Their labels are pgrust,
nushell, rg-aot, forward-anchored-tls, pgrust-sha1-inline8, ruff and
nushell-type-relations. Preserve any unresolved regression above 5%. Use the
benchmark lock; do not run validation concurrently with these measurements.
Only after all required checks may retention be considered. Large-codebase
adoption, broader edit classes and complete OS/thread/unwind support remain
separate unfinished work.
