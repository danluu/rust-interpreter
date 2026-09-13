# Explicit source-freeze continuation

`planned-freeze-source-continuation-01.json` is an **unexecuted** recovery plan
for `mono-production-build-02/stages/freeze-source-01`. That attempt built the
bootstrap helper and extracted the already pinned formatter components, then
both `x fmt --check <paths>` and `x fmt <paths>` failed because this bootstrap
rejects path arguments. No formatting or compiler source commit completed.

The standalone `freeze-source-continuation.py` keeps the original driver,
plan02, input hashes and failed receipts unchanged. It invokes the existing
formatter exactly as `src/bootstrap/src/core/build_steps/format.rs:25–45` does:

```text
build/aarch64-apple-darwin/rustfmt/bin/rustfmt --config-path SOURCE --edition 2024 --unstable-features --skip-children [--check] SIX_REVIEWED_FILES
```

Before use, under the canonical workload lock, it verifies the entire existing
formatter extraction against the two pinned archive components in bootstrap's
overlay order, including executable/library bytes and the exact generated
stamp. It neither downloads nor repairs tools. It checks the original six
patched source hashes, runs check/format-if-needed/check, and rejects changes
to unrelated tracked source. The formatter inventory and every child receipt
and output are retained. Admission and child execution use the original
environment, Python identity and `owned_stage` supervision.

Successful completion creates an actual Git commit, records its source and
backtrace inventories and both patch digests, runs the original driver's
`check_frozen`, and writes its ordinary `source.json` and successful
`freeze-source` completion entry. The receipt explicitly links this recovery
plan and the failed attempt. Later build stages still use the original driver
and its existing checkpoints.

After review, run from this owned driver checkout without an outer flock:

```sh
python3 experiments/stable-cgu/freeze-source-continuation.py --plan /Users/danluu/dev/rust-interp-stable-mono-compiler-build-20260913/experiments/stable-cgu/planned-freeze-source-continuation-01.json
```

Preparation validation was limited to Python AST parsing, original input hash
equality and whitespace checking. The continuation, formatter, compiler builds
and tests have not been executed by this preparation step.
