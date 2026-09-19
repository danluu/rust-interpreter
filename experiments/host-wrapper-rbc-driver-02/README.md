This driver runs the held five-test host-wrapper RBC fixture against an actual
published tool key, the qualified runtime `f031…`, and prepared std `f636…`.
The fixture and its three original donor modules remain unchanged. No application
benchmark, holdout, tool build, installation, or standard-library preparation is
part of this driver.

`bind.py` accepts the actual publication receipt, published-tools result, normal
parent receipt, tool key, and exact source-manifest hash. It authenticates saved
metadata and closed publication children, then reconstructs the complete declared
runtime/std/tool/Cargo payload table without reading those payloads or starting a
process. The binding contains required actual values, never future success pins.

`execute.py` normally waits `run.py`, which alone acquires the canonical lock
with a 600-second bounded wait. Before the suite, and after it closes, the driver
hashes the complete declared inputs and invokes the existing ordinary runtime,
installed-tools, host capability, and prepared-std readers. The installed reader
retains its original R path. Source authentication covers every dynamically
loaded donor and reader module before import. The std reader checks complete
saved membership/stamps; its redundant byte reread is disabled because the driver
has just authenticated the complete payload table itself.

The suite runs these exact five test methods, once each:

- `test_cargo_shared_library_macro_input_spans_error_and_restoration`
- `test_macro_cfg_debug_and_overflow_checks`
- `test_native_debug_overflow_ub_cfg_generics_inline_and_drop_effects`
- `test_uncalled_macro_errors_and_restoration`
- `test_uncalled_type_borrow_const_and_position_changes_reject_then_restore`

Passing requires five matching full unittest IDs, zero failures/errors/skips,
zero expected failures/unexpected successes, no observation violations, normal
closure, and identical complete before/after input maps. The inherited tests
compare exact off/on RBC bytes, run both interpreter and JIT, check complete
diagnostics and restoration, and compare real compiler-boundary roles/arguments.
The source-derived expectation is about 189 direct commands; that estimate is
not a fabricated result or a success predicate. An enforced maximum of 256
direct commands applies before starting another command and at final readback.

The resource policy is entry free space at least 16 GiB, an observed stop
threshold of 9 GiB, and final floor of 8 GiB. Owned logical and allocated output
must each stay within 1 GiB, with at most 65,536 entries. This counts the fixture
work, result, and normal-parent output trees. The suite threshold is 600 seconds;
each direct `workflow_io.capture` command has a 30-second observed threshold.
The suite threshold excludes full immutable-input authentication. A Cargo
command can own multiple nested compiler processes; the 30-second observation
is for that whole direct command, not an independently imposed timeout on each
nested compiler. The parent samples every 0.25 seconds; the suite also checks
boundaries. A violation records STOP, blocks further fixture commands, and waits
normally for the already running command. No signals, retries, automatic cleanup,
hard time quota, atomic disk reservation, CPU limit, or memory cap are implied.

Run all entrypoints with `/opt/homebrew/bin/python3 -B` from the original R cwd.
`bind.py --sources-sha256 … --tool-key … --publication-receipt-sha256 …
--published-tools-sha256 … --publication-execution-sha256 …` creates the fresh
`binding.json`. After review, `execute.py --binding <absolute binding.json>
--binding-sha256 … --tool-key …` is the one execution entrypoint. The base child
environment is the saved qualified std environment, with only TMPDIR moved into
the owned work tree; the suite receives explicit tool/runtime/std/VM/Cargo paths.
Ambient `CARGO_PROFILE_*`, loader variables, and `RUST_INTERP_*` are not inherited.

The result namespace is `ROOT/results/host-wrapper-rbc-fixture-02` and the normal
parent namespace is `ROOT/.work/host-wrapper-rbc-execution-02`. Parent status
`closed` is saved immediately after OS wait, before terminal decoding; `passed`
requires the complete successful driver association. The suite result retains
the actual test IDs, all command receipts/raw hashes/observation rows, and actual
loaded source identities. Raw references bind bytes rather than transient write
stamps because the held fixture rewrites identical raw streams after capture.
Future Ruff correctness and performance remain separate qualifications.

Successor02 preserves the failed01 source, binding, and evidence. Its only driver
change is the fresh fixture/output/parent namespace. Root-owned fixture02 changes
Cargo diagnostic presentation to full JSON so the unchanged complete-diagnostic
collector can compare the generated-error history. All five tests and resource
predicates remain required. No successor execution is implied by these sources.
