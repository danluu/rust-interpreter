# Native stock-store bridge baseline

The frozen `63f70679` source subsequently passed all four Python boundary
controls and the two native commands, with all four real bridge tests passing
in one unfiltered serial process. The earlier zero-test Python identity setup
failure is retained. See the [complete baseline evidence](../../../results/span-bridge-native-baseline-01/README.md).

`baseline.py` prepares a narrow execution path for the unchanged `c964a9e0`
fixture. It uses the already installed complete Cmono58 compiler
`f9fb3e5f59b8567fffd32c936a9864d0baee77038574236710fbcec75a57d33f`
and that installation's actual native `proc_macro`, `test` and standard
libraries. The library span store is the original BTreeMap implementation.
Neither the span patch nor any compiler source is modified or rebuilt.

This qualifies only the existing real `Client::run1` fixture against the stock
store. It does not qualify the proposed span store, rustc_expand's server, a
proc-macro dylib/caller history, exported execution, or performance. The existing
four pure expectation tests also do not substitute for these native controls.
The wider matrix in the adjacent README remains separate work.

Exactly two native commands run, in order:

```text
COMPILER/sysroot/bin/rustc --test --edition=2024 \
  --crate-name span_bridge_baseline --sysroot COMPILER/sysroot \
  --error-format=json --emit=link,dep-info=WORK/artifacts/bridge.d \
  WORK/source/experiments/proc-macro-span-handles/integration/bridge.rs \
  -o WORK/artifacts/span_bridge_baseline
WORK/artifacts/span_bridge_baseline --test-threads=1 --nocapture --format=pretty --color=never
```

The single unfiltered harness process preserves shared cross-test lifecycle
observations. It must report each of the four exact names in `baseline.TESTS`
once, with 4 passed and zero failed, ignored, measured or filtered. The fixture
itself covers both execution strategies where safe, stale same-thread handles,
exact RPC/destructor ordering, nested execution and panic recovery. Intentional
panic output remains in raw stderr. No per-test process, expectation rewrite,
name filter, optimizer override or execution-strategy flag is introduced.

`baseline-inputs.json` binds every original fixture/document/patch byte to its
Git checkpoint, and binds the original bridge source files in installed
rust-src. At admission the existing complete-compiler loader checks the owned
immutable installation and all stamps. The runner additionally hashes the
actual compiler, selected native libraries and bridge sources, and checks them
before/after every command. It snapshots the full ready manifest, fixture,
runner, shared helpers, Python identity, exact environment and command plan.
The environment is an explicit allowlist; inherited Rust/Cargo/test flags,
SDK overrides and user PATH are not forwarded. Dynamic-loader overrides cause
rejection. Native compilation otherwise keeps ordinary rustc test defaults;
the prebuilt native std's original profile is recorded from provenance.

Run from the owned checkout containing this driver, after source review and
workload admission, with fresh run IDs:

```sh
python3 scripts/supervise_experiment.py --run-id span-bridge-baseline-supervisor-01 -- \
  python3 experiments/proc-macro-span-handles/integration/baseline.py \
  --compiler-root /Users/danluu/dev/rust-interp-semantic-reuse-20260913 \
  --run-id span-bridge-baseline-01 \
  --workload-lock /Users/danluu/dev/rust-interp/.work/benchmark.lock \
  --lock-wait-seconds 600
```

The outer existing supervisor holds no workload lock. The driver acquires the
canonical lock once and uses `owned_stage.run` for exact child identities,
raw stdout/stderr, finally-wait cleanup and the existing 8 GiB capacity floor.
Compiler/test failures retain their attempted-command receipts and prevent a
passing result; retrying requires a fresh run ID. The generated native binary,
dep-info, compiler identity and all fixture sources remain under the new work
directory. Future compact publication should retain the binary hash and exact
raw results without presenting the binary as a patched compiler artifact.

Four focused Python boundary controls are provided in `test_baseline.py`:
exact unfiltered result validation, two-command native routing, environment
isolation, and rejection of changed native span-store source. Both these tests
and the native baseline passed on the frozen source recorded above. The
original source-only manifest and snapshots retain their historical unrun
status; the linked execution receipts establish the subsequent result.
