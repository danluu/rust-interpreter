# Stable per-MonoItem placement screen

The separately selected `stable-mono-cgu` policy compares one qualified custom
compiler and one matching exporter/wrapper/VM build in three independent Cargo
histories. Module grouping is explicitly **off/off/off**; per-MonoItem placement
is explicitly **off/on/off**. Compiler and tool keys and every actual binary are
identical across the arms. The baseline is the same newly built compiler with
this policy disabled. Defaults and the existing stable module-grouping screen
remain unchanged.

Admission requires a passed `stable-mono-cgu-integration-v1` receipt from the real
custom-compiler integration harness: its existing 36 commands, 22 launcher and
11 public controls, 24 expected rejection controls, strict structured diagnostic
comparison with zero presentation gaps, native and guest edits/restoration, and
bytecode checks. It must name the exact measured compiler/tool and both std
identities. The receipt binds the complete retained command and child histories
and a compiler-argument proof. That proof links actual native-host and selected
guest final argument records in both modes to the recorder's preserved NUL bytes;
Cargo's command before wrapper routing is insufficient. A preliminary diagnostic
comparison, old module-only integration result or std smoke result is rejected.
Recording is confined to qualification; the measured commands omit it.

Admission also requires the independent `std-source-observables-v2` result for
the same compiler, tools and both std keys. Its real source-position histories,
second-prefix copies, missing/corrupt source controls and native/exported
proc-macro observables are separate from the 36-command integration. The screen
validates this result and freezes every linked evidence file around all timed
commands; neither prerequisite may substitute for the other. The current
`native-rows-exact-guest-bitmask-v1` transport retains all original 57 controls
and adds four real wrong-expectation executions, for 61 commands. Native raw
observations supply exact expected bytes/coordinates; the actual exported
program compares all ten fields and returns their bitmask. Generated source,
native rows, actual bytecode and actual output are bound by the same typed
validator. The old stdout-based57-command policy cannot qualify this screen.

Both prepared std directories must use `source-paths-v2` and the authoritative
`std_mir_source_paths.load` validator, in `stable-mono-cgu:off` and
`stable-mono-cgu:on` namespaces. Their source-containing sysroots, compiler/Cargo
configuration and setup evidence are verified before admission and guarded at
every command boundary. They share the same qualified compiler and standard
source inventory. Std preparation remains outside the application placement
policy; its `full_presentation_qualified: false` smoke-only scope is retained.
Only the separate real strict integration receipt qualifies diagnostic behavior.

After importing the exact qualified tools/compiler and preparing both std keys,
the command template is:

```sh
python3 benchmarks/experiments/strict-warm-build/screen.py \
  --run-id strict-warm-mono-cgu-screen-01 \
  --source "$OWNED_NUSHELL_SOURCE" --candidate-policy stable-mono-cgu \
  --baseline-tool-key "$TOOLS" --candidate-tool-key "$TOOLS" \
  --compiler-key "$COMPILER" --compiler-qualification "$STRICT_RESULT_JSON" \
  --source-observables "$SOURCE_OBSERVABLES_RESULT_JSON" \
  --std-mir-ready "$OFF_READY_JSON" --candidate-std-mir-ready "$ON_READY_JSON" \
  --lock-wait-seconds 45
```

This is an unexecuted template, not a prepared or admitted run. The strict
qualifier, source-observable prerequisite and v2 std preparation must pass before
it can run. Custom Cargo,
module grouping, host-macro optimization, frontend-worker tuning, demand
retention and borrow-check shortcuts cannot be combined with this screen.

The existing 27-command order, all 14 original tests, wrong production edit,
compiled recovery, five new cumulative valid edits and compiled final restoration
are unchanged. All arms retain the same four Cargo jobs, two suite workers,
Cargo profiles, guest flags, limits and runtime options. Every timed command
includes launcher validation, Cargo and required compiler/build-script work,
VM setup, tests and receipt I/O. Bytecode, entry catalogs, outcomes and program
outputs must match across arms. Paired wall/CPU and duplicate-baseline noise are
reported without subtracting work. The 0.500-second gate is unchanged; this
screen supplies neither final latency qualification nor holdout evidence.

Saved assessment must consume `stable_mono_qualification.validate_qualification`
with archived payload access, reconcile the frozen tools/compiler and v2 std
proofs, enforce these exact selectors and launcher receipts on all 27 rows, and
retain all qualification and setup evidence. Std readiness must never be
relabeled full presentation qualification. No saved-assessor implementation is
duplicated by this extension.
