# Frozen-link controls (source-only, unrun)

This small runner launches exactly one Python child for the 24 real filesystem
tests in `runtime-frozen-link-reader-01`. It never imports the runtime producer,
saved auditor, compiler or provider modules. There is no recursive harness or
compiler admission. No canonical lock is acquired: this scope is temporary
directory unit tests only.

After source review, the sole invocation is:

```
cd /Users/danluu/dev/rust-interp-semantic-reuse-20260913
/opt/homebrew/bin/python3 -B experiments/runtime-frozen-link-controls-01/run_once.py
```

`results/runtime-frozen-link-controls-01` must be absent. The runner requires
256 MiB free and observes a 128 MiB floor; its owned output namespace is capped
at 8 MiB. The child has 30 CPU seconds, a 60-second parent observation window,
a 256 KiB file limit and no core dumps. The parent never signals or retries a
child. If it is still live at the observation deadline, the record says so and
no successful proof is produced.

The child authenticates exact helper/test bytes before import, derives all
24 test IDs from source, and records every actual unittest name. Its Python
audit hook permits creation, rename, removal and symlinks only within owned
`results/runtime-frozen-link-controls-01/tmp`; target escapes are rejected.
Descriptor-relative cleanup is authorized by matching its held directory inode
to an ordinary directory in that bounded owned tree. Ordinary read-only opens
remain available for Python and the authenticated helper's held-descriptor
resolution. Workspace source reads are restricted to the declared modules and
owned temp tree; absent bytecode lookups do not authorize cached module reads.
Subprocess, exec/fork, network, signals, ctypes, hard links and environment/cwd
mutation are denied. No source/provider write route is granted.

The child prints verbose unittest output and one `FROZEN_LINK_CONTROL_RESULT`
JSON footer. The parent requires all exact names once, zero skips/errors/failures,
empty stderr, matching child/parent PIDs, empty owned TMP after cleanup, and
unchanged source hashes plus seven-field identities. Exact passed and observed
environments are retained separately; no startup normalization is performed.

The closed result namespace contains copies of `run_once.py`, `child.py`,
`plan.json`, plus `started.json`, `record.json`, `source-before.json`,
`source-after.json`, `stdout`, `stderr`, `result.json` and `manifest.json`.
`manifest.json` lists every other ordinary top-level file; `tmp` must be empty.
`result.json` has status `verified-frozen-link-controls` only on a complete pass,
`tests: 24`, exact `test_names`, full `sources`, the original child proof, and
path/SHA references named `record`, `source_before`, `source_after`, `stdout`,
`stderr`, and `plan`. The actual `record` retains command/cwd/environment, parent
and child identity, observed closure/returncode, limits, raw file identities and
any observation failures.

A fresh saved-audit successor must authenticate the runner/child/helper/test
sources and the exact closed result and record, recheck the listed source/raw
membership and names, and bind the helper source SHA before import. This result
is not the generic `reader.controls` schema and must not be passed as one.
No future result SHA is embedded here. These tests qualify only the link helper;
the successful original preflight and a separate saved audit remain required.
