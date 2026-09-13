# Shared immutable standard-library preparation

The first per-MonoItem screen stopped after its three cold commands. All 14 tests
passed in every arm, but the off/on bytecode differed because the compiler imported
standard-library source paths from two different physical prepared sysroots.
The structured comparison found 153 trap-message path differences and 18
caller-location path strings in the constant data. Baseline and duplicate bytes
matched. That history remains failed; no edited timings or latency qualification
were obtained, and no artifact is normalized to bypass its parity check.

Std preparation already uses identical compiler, sources, Cargo recipe, features,
profile and flags in both modes. Neither application placement option is applied
during that preparation. This amendment shares that immutable dependency while
retaining separate application Cargo and incremental histories. It changes no
application source, test selection, compiler checks, codegen-unit count, profile,
macro policy, remapping flags, diagnostic comparator or 0.500-second gate.

The explicit launcher selection is `source-paths-v2-shared`. Its preparation
namespace is `immutable-source-paths-v2:shared`; its identity policy is
`metadata-sysroot-v2-shared-source-paths-release-backtrace`. These are new keyed
values. Old v2 readiness is never relabeled or copied into the new namespace.
The existing authoritative loader still checks the complete compiler/source,
Cargo/configuration, immutable metadata/source inventories and setup receipts.
The two preparation probes retain their setup-only scope.

The launcher translates only the preparation namespace. The application identity
still contains `stable-mono-cgu:off` or `stable-mono-cgu:on`, the exact shared std
key, the actual compiler/tool identity and its separate screen cache namespace.
Every measured launch reports the new std identity policy and exact physical
sysroot. The shared screen requires identical full readiness in all arms, and
qualifiers require equal key/sysroot/target while retaining actual off/on compiler
argument proof and all existing source, execution, error and restoration controls.
Historical per-mode v2 assessment remains supported through its original policy.

Run the following only after the combined source is reviewed and frozen in
PRIMARY, under the existing supervised canonical workload discipline. These are
templates, not executed commands or predicted keys. `$COMPILER` is the unchanged
qualified compiler; `$TOOLS` is the newly qualified actual tool composition.

```sh
python3 scripts/std_mir_source_paths.py --compiler-key "$COMPILER" \
  --namespace immutable-source-paths-v2:shared \
  --run-id mono-production-std-shared-01 \
  --workload-lock /Users/danluu/dev/rust-interp/.work/benchmark.lock \
  --lock-wait-seconds 600

# Read SHARED from the successful preparation receipt; do not predict its key.
python3 scripts/qualify_custom_compiler.py --compiler-key "$COMPILER" \
  --tool-key "$TOOLS" --partitioning-policy stable-mono-cgu \
  --std-mir-policy source-paths-v2-shared \
  --std-mir-off-key "$SHARED" --std-mir-on-key "$SHARED" \
  --run-id mono-production-integration-shared-01 --lock-wait-seconds 600

python3 scripts/qualify_std_source_observables.py --compiler-key "$COMPILER" \
  --tool-key "$TOOLS" --std-mir-policy source-paths-v2-shared \
  --std-mir-off-key "$SHARED" --std-mir-on-key "$SHARED" \
  --run-id mono-production-source-observables-shared-01 --lock-wait-seconds 600
```

Only after both new results pass may a fresh 27-command screen use the same
`ready.json` for `--std-mir-ready` and `--candidate-std-mir-ready`. All commands,
all 14 tests, the deliberately wrong edit, compiled recovery, five fresh edits,
restoration and exact cross-arm bytecode parity remain unchanged. Preparation
costs are retained separately; no work is subtracted from measured latency.

Focused source tests cover actual synthetic shared publication and load without
new children, old-policy relabel rejection, changed physical paths, strict
qualification launcher binding, complete archived std proof, and explicit mode
flags with shared std keys. Real preparation/36/61/screen histories are still
required; these source tests do not substitute for them.
