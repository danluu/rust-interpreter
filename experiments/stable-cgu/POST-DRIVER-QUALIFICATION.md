# Production per-item compiler handoff

This is an unexecuted post-driver sequence. The actual compiler source commit is
**58e1e1f5311f4424ea81def4763081f6da62d9b3**. It is neither an installation key nor
an interpreter tool key. The original twelve driver stages remain authoritative;
this document begins only after their final `complete` receipt passes.

Use PRIMARY `/Users/danluu/dev/rust-interp-semantic-reuse-20260913` for installation,
tool compilation, both prepared std namespaces and every qualification/screen.
The immutable exporter/wrapper records embed that physical installation prefix.
Do not build the tools in this handoff worktree and copy them to PRIMARY.

Before installation, validate all twelve hashes in DRIVER's
`.work/mono-production-build-02/completed.json`, their passing stage receipts,
the actual `source.json` commit above, and the complete stage's package/provenance
paths. The source-freeze entry intentionally points to the explicit successful
continuation; the earlier rejected formatter attempt remains evidence. The
package must be first-production stage2, carry `std_source_paths` with truthful
`/rustc/58e1e1f5311f4424ea81def4763081f6da62d9b3` and corresponding `/rustc-dev/`
prefixes, and retain its native/strip controls and raw native source probe.
Rehash the package against the complete/package receipts before importing.

Freeze PRIMARY's actual Rust sources and all participating helper scripts after
the worker campaign permits integration. Keep them fixed through tool build,
workspace check, strict36, observable57 and the first screen27. A source change
requires the ordinary rebuild/requalification appropriate to that change; never
relabel an older tool's producer. Save the actual frozen Git revision plus file
hashes. No worker source or original DRIVER input changes are part of this work.

All setup is serial under the canonical existing lock
`/Users/danluu/dev/rust-interp/.work/benchmark.lock`. Verify PRIMARY's local alias
resolves to that same file before any helper using its local alias. Use the
existing `scripts/supervise_experiment.py` to retain each outer command, giving
every attempt a fresh ID. The outer supervisor must not hold another flock while
a child helper acquires it. The importer currently has a fixed45-second admission;
coordinate its start when the lock is free. Do not change the frozen importer or
wrap it in an independently held flock. Other setup commands below request600
seconds. Preserve failed attempts and partial prefixes without automatic retries.

The following commands run from PRIMARY. `MONO_PACKAGE` and `MONO_PROVENANCE`
come from the successful driver complete receipt; the expected current paths
are DRIVER `.work/mono-production-build-02/packaged-stage2-01` and
`.work/mono-production-build-02/package-01/provenance.json`. Every key variable
must come from the named command's actual successful result, never from a source
fingerprint or a predicted build output.

```sh
python3 scripts/custom_compiler.py \
  --install-from "$MONO_PACKAGE" --provenance "$MONO_PROVENANCE"

# MONO_COMPILER_KEY = returned compiler_key. Validate installed ready.json,
# provenance source commit, complete file inventory and both -Z option proofs.
python3 scripts/build_custom_tools.py --compiler-key "$MONO_COMPILER_KEY" \
  --run-id mono-production-tools-01 --lock-wait-seconds 600

# MONO_TOOL_KEY = .work/mono-production-tools-01/result.json tool_key.
python3 experiments/stable-cgu/check-custom-workspace.py \
  --compiler-key "$MONO_COMPILER_KEY" --tool-key "$MONO_TOOL_KEY" \
  --run-id mono-production-workspace-01 \
  --workload-lock /Users/danluu/dev/rust-interp/.work/benchmark.lock \
  --lock-wait-seconds 600

python3 scripts/std_mir_source_paths.py --compiler-key "$MONO_COMPILER_KEY" \
  --namespace stable-mono-cgu:off --run-id mono-production-std-off-01 \
  --workload-lock /Users/danluu/dev/rust-interp/.work/benchmark.lock \
  --lock-wait-seconds 600
python3 scripts/std_mir_source_paths.py --compiler-key "$MONO_COMPILER_KEY" \
  --namespace stable-mono-cgu:on --run-id mono-production-std-on-01 \
  --workload-lock /Users/danluu/dev/rust-interp/.work/benchmark.lock \
  --lock-wait-seconds 600

# MONO_STD_OFF_KEY / MONO_STD_ON_KEY = each setup result's actual key.
python3 scripts/qualify_custom_compiler.py --partitioning-policy stable-mono-cgu \
  --compiler-key "$MONO_COMPILER_KEY" --tool-key "$MONO_TOOL_KEY" \
  --std-mir-policy source-paths-v2 --std-mir-off-key "$MONO_STD_OFF_KEY" \
  --std-mir-on-key "$MONO_STD_ON_KEY" --diagnostic-comparison strict \
  --run-id mono-production-integration-01 --lock-wait-seconds 600

python3 scripts/qualify_std_source_observables.py \
  --compiler-key "$MONO_COMPILER_KEY" --tool-key "$MONO_TOOL_KEY" \
  --std-mir-off-key "$MONO_STD_OFF_KEY" --std-mir-on-key "$MONO_STD_ON_KEY" \
  --run-id mono-production-source-observables-01 --lock-wait-seconds 600

# MONO_NUSHELL_SOURCE = explicitly admitted owned Nushell source, quiescent.
python3 benchmarks/experiments/strict-warm-build/screen.py \
  --candidate-policy stable-mono-cgu --compiler-key "$MONO_COMPILER_KEY" \
  --baseline-tool-key "$MONO_TOOL_KEY" --candidate-tool-key "$MONO_TOOL_KEY" \
  --std-mir-ready "$PWD/.work/std-mir/$MONO_STD_OFF_KEY/ready.json" \
  --candidate-std-mir-ready "$PWD/.work/std-mir/$MONO_STD_ON_KEY/ready.json" \
  --compiler-qualification "$PWD/.work/mono-production-integration-01/result.json" \
  --source-observables "$PWD/.work/mono-production-source-observables-01/result.json" \
  --source "$MONO_NUSHELL_SOURCE" --run-id strict-warm-mono-production-screen-01 \
  --lock-wait-seconds 600
```

The custom workspace helper fills one real gap: `scripts/check_workspace.py`
clears `RUSTC` and selects the public compiler, so it cannot establish this
matched custom workspace result. The new helper binds the installed tool
composition/current source, uses the same compiler-key Cargo target and ordinary
release/jobs2 flags, selects matching installed rustdoc for doctests, retains
raw version/test outputs and source snapshots, and reports the actual test
counts. It checks the installed tools and original target binaries before and
after. It does not publish tools or replace strict36. Its three pure boundary
tests are prepared but unexecuted.

Stdv2 setup preserves `-Zalways-encode-mir=yes -Zforce-unstable-if-unmarked`, the
backtrace feature, release profile, pinned Cargo3c0 binary/version/library proof,
and jobs2. Its existing W/library plus root-W trim recipe uses the actual
compiler source commit. Both arms get the identical metadata-only recipe and
separate namespace-derived keys. Native and prepared raw E0080 snippet probes
must pass before readiness; setup explicitly is not full presentation
qualification. Do not export custom `RUSTC`, `RUSTDOC`, loader flags, experimental
flags or trim/remap environment globally between commands.

Strict36 must report all36 complete commands, passing semantic controls,
`full_presentation_qualified=true`, strict diagnostics and restored source. It
includes the ordinary pinned public compiler reference, host build-script and
proc-macro paths, edits/restoration, and uncalled type/borrow/const/panic errors.
The diagnostic-only compiler mappings must preserve actual snippets; no derived
JSON substitution or missing-snippet normalization is accepted.

Observable57 is independently required. Validate its passed receipt with
`std_source_observables.validate_source_observables`, bound to these same actual
compiler/tool/std identities. It retains original/second-prefix native and
prepared raw source histories, full copy proofs, deliberate invalid-source
rejections and application observables. Only the explicit application-map
sensitivity control may change `Span::file`; std-only mappings must preserve
the application values. The screen independently validates both this receipt
and `stable_mono_qualification.validate_qualification`; neither can substitute
for the other.

Admit disk separately before each phase using actual package and copied-prefix
sizes plus the8-GiB floor. Installation requires another complete package copy;
observable57 intentionally makes an independent native prefix and both prepared
prefix copies. Its controls and the screen also allocate fresh Cargo targets.
Do not assume the driver's36-GiB initial admission reserves later space. Retain
source, package, installation, publication and raw evidence; any later retirement
needs exact ownership/dependency review.

Screen27 keeps the same compiler and actual tools across off/on/off arms,
module grouping explicitly off, distinct caches, five cumulative fresh edits,
wrong-edit/recovery/final-restoration controls and all14 original Nushell tests.
It preserves jobs4, the existing VM flags, two suite workers and resource limits;
no custom Cargo, worker, macro, retention or diagnostic instrumentation is added.
Complete-command timers enclose production launcher/Cargo/compiler/VM checking
and execution. Frozen-input and evidence audits remain outside these timers as
in the existing protocol. Keep every result, including failures and timings over
0.5 seconds. This is still a mechanism screen, not final target/holdout adoption.

After source restoration, run the existing saved assessor command below under
an outer canonical-lock holder with normal captured-child supervision (the
assessor itself does not acquire a lock):

```sh
python3 benchmarks/experiments/strict-warm-build/assess_owned_screen.py \
  "$PWD/.work/strict-warm-mono-production-screen-01" \
  --run-id strict-warm-mono-production-screen-01
```

Archive both prerequisite histories, full stdv2 metadata/source/provenance
records, source snapshots, all27 receipts/outputs/artifacts and the exact
installed associations. Independently verify the archive members before
publishing conclusions or retiring any generated cache. The remaining gates
are actual executions; this source-only handoff makes no correctness, speedup
or sub-0.5-second claim.
