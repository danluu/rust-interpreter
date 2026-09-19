# Real proc-macro compiler fixture: output-path correction

This successor is unrun. Its nine Rust files are byte-identical to the
independently reviewed attempt01 fixture. The same installed-stock and Arena04
client libraries, matching compiler/sysroot, nine cases per arm and twenty
serial compiler calls remain in the plan. No fixture assertion, expected error,
warning policy, dependency check or resource limit is relaxed.

Attempt01 stopped after its first stock dylib compiler returned zero. The strict
diagnostic checker rejected Rust's warning about combining `-o` with multiple
output types. No caller or candidate compiler ran. The original source, result
directory and produced stock files remain unchanged. A separate retained failure
capsule is at `ROOT/results/proc-macro-arena-compiler-01-failure`; `plan.json`
binds its review and original manifest, plus the original failed execution.

Each new command supplies its output paths directly:

- Dylib: `--emit=dep-info=<exact .d path>,link=<exact .dylib path>`.
- Caller: `--emit=dep-info=<exact .d path>,metadata=<exact .rmeta path>`.

The `-o` option and its value are removed. All other arguments remain identical
after substituting the fresh02 source/work/output paths. The entire one-shot
runner function/class AST is unchanged; only `SOURCE`, `WORK`, `OUT` and
`PLAN_SHA` assignments differ. Exact source and plan diffs are retained here.

The runner still requires 24 GiB at each compiler admission, a 600-second
canonical wait, 9 GiB live stop/8 GiB floor, finite child CPU and observer bounds,
64 MiB per file and 128 MiB fresh work. It records closure before output hashes,
preserves full raw JSON, rejects unexpected errors and warnings, checks exact
stable diagnostic parity and dependency selection, and rechecks each dylib
before and after every caller. It sends no signals, makes no retries and never
changes an existing installation. A new root review and once-run decision remain
necessary; no actual result, performance claim or distribution qualification is
provided by these sources.
