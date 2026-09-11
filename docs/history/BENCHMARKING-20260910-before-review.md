> Historical snapshot before the September 10 review. For current findings see [STATUS.md](../../STATUS.md).

# Benchmark methodology

## Current custom interpreter/JIT workflow

`scripts/bench_e2e_workflow.py` measures complete commands after five cumulative
production-body refactors in owned, pinned project snapshots. It retains all
selected original tests unchanged, first verifies that every engine rejects a
wrong production edit, and restores source afterward. Native and custom modes
each use one command with `--batch`. Warm results are edited build/test commands.
The custom engines keep ordinary type and borrow checking and execute through
the project's bytecode interpreter or direct AArch64 emitter.

For example, the complete eighteen-test folded-trie workflow uses:

```sh
python3 scripts/bench_e2e_workflow.py --project fre --workflow folded-literal-trie \
  --batch --std-mir --trap-unsupported-calls --inline-leaves \
  --guest-mir-opt-level 3 --instruction-limit 100000000000 --run-id NEW_RUN_ID
```

Paired comparisons use `--baseline-tool-key`, `--comparison-engine jit` and,
when isolating runtime changes, `--expect-identical-bytecode`. Match leaf inlining
with `--baseline-inline-leaves`. Every executed bytecode artifact is retained.
Explicit guest MIR flags apply to custom modes; native keeps its test profile.
Five shared-host pairs are not confidence intervals. Separate medians of stages
need not sum to a median total, or equal a median paired difference.

Use `--cycles 3` or more for repeated edits. Each cycle rebuilds original source,
checks the wrong edit, and replays all five real edits. Only the first original
command is cold; later original commands are labeled anchors. Each mode must
have a different source hash from its preceding compilation. Three cycles rotate
every edit through all three mode positions. Reports include child user/system
CPU time, paired differences and per-edit min/median/max; these are descriptive
measurements, not confidence intervals. Cache history evolves across cycles.

The [first repeated token run](../../results/paired-repeated-token-01/assessment.md)
demonstrates why both source and artifact hashes matter: corresponding engines
produced identical bytecode, but returning to the same source after the first
cycle changed constant/data layout. Do not assume identical source implies an
identical artifact across different compiler-cache histories.

`--cargo-timings` enables Cargo's compilation-unit reports in every mode. Report
generation stays inside the command timer. The harness copies each report after
timing and records its hash under the raw run's `cargo-timings/` directory. These
reports help distinguish selected-target compilation, other compiler invocations
and time before compilation begins. Treat such runs as diagnostic comparisons;
they include report generation. [Cargo's timing-report documentation](https://doc.rust-lang.org/cargo/reference/timings.html).

The sections below preserve the earlier Cranelift and publication experiments.

The benchmark corpus is pinned in `benchmarks/corpus.json`. Public projects are
pgrust, Ruff, Nushell, and fre; rg-aot is a private local snapshot. No existing
working tree is built or edited. Run logs and private compiler diagnostics stay
under ignored `.work/`. All commands use the same pinned compiler, four build
jobs, and separate Cargo target directories per project/backend/run.

The host is an Apple M5 Max with 18 logical CPUs and 48 GiB RAM. It is a shared
development machine. No other workload is stopped or reprioritized. Samples
include load averages before and after each build, wall time, aggregate child
CPU time, source digest, compiler version, source revision, dependency lockfile
digest, rebuilt/fresh Cargo artifact counts, cache statistics, and execution
checks. Peak aggregate memory is not yet measured.

## Earlier baseline commands

```sh
python3 scripts/prepare.py cg-clif rg-aot fre pgrust ruff nushell
python3 scripts/build_backend.py
python3 scripts/prepare_fre_driver.py
# Fetch dependencies once, outside timing, for each source manifest.
python3 scripts/bench.py rg-aot fre pgrust ruff nushell --run-id experiment-01 --repeats 5 --debug repository
python3 scripts/runtime.py experiment-01
python3 scripts/report.py experiment-01
```

The separate macOS publication comparison uses the same experimental Cargo
binary with the preservation flag off and on, alternating order. Each measured
sample must rebuild zero artifacts and execute the expected program. Enabled
samples must retain the executable's inode. This isolates publication from a
Cargo version or build-optimization change:

```sh
python3 scripts/prepare.py cargo
python3 scripts/build_cargo.py
python3 scripts/bench_publication.py experiment-01 rg-aot fre pgrust ruff nushell
python3 scripts/validate_publication.py
```

These are direct-Cargo measurements. The Python launcher's configuration and
binary-integrity checks are additional overhead and are not included in them.

The timed Cargo commands use `--locked --offline`. `prepare.py` fetches source
snapshots; it does not itself fetch all registry dependencies. Use `cargo
+nightly-2026-09-08 fetch --locked --target aarch64-apple-darwin` in each source
directory before timing. The fre driver generates an independent lockfile from
the already downloaded packages.

## Comparisons and limits

- **LLVM / Cranelift / cached Cranelift:** same compiler, source, Cargo features,
  standard library, profile, and panic policy. Cached and uncached Cranelift use
  the same backend binary. The optional cache flag is the treatment.
- **Panic policy:** the Cranelift experiments use `panic=abort`, and the matched
  LLVM control uses the same setting. They do not qualify pgrust's database
  behavior, which relies on unwinding. `llvm-unwind` is available separately.
- **Profiles:** repository optimization and debug settings are retained by the
  current default. Incremental compilation is explicitly enabled, including for
  pgrust, whose repository disables it. Use `--incremental repository` for the
  repository policy. Target rustflags are normalized by the measurement harness;
  in particular Nushell's target-specific CPU setting is overridden for all
  compared variants. The development launcher separately preserves Cargo config.
- **Cold:** an empty target directory and empty function cache, with downloaded
  dependencies and installed toolchain/stdlib. OS filesystem caches are not
  flushed. There is one cold observation per backend per run; no confidence
  interval is claimed for it. Cold order is fixed as LLVM, Cranelift, then cached
  Cranelift in the main matrix; only warm samples alternate order.
- **Warm:** no-op, body edit, revert, then no-op. Each body edit has a different
  immediate multiplier and a `black_box` operand. The program must print the new
  arithmetic result before its timing is accepted. Reverts intentionally exercise
  previously seen code. The compiler order reverses between rounds.
- **Edit coverage:** these are synthetic executable body probes. Most are in
  binary entry points; fre's edit is inside its library and is reached through a
  separate consumer. These are not representative edit-history traces, public
  API changes, or trait/coherence invalidation benchmarks.
- **Runtime:** each build has a smoke check. `runtime.py` separately measures
  bounded search, lint, and Nushell pipeline workloads with checked results and
  alternating order. pgrust has only compile/link/startup coverage at this stage.
- **Success:** a sample requires successful compilation, expected edited-program
  output, and its project-specific runtime check. Failures are kept and excluded
  from performance comparisons. No-op builds may not rebuild any Cargo artifact.

## Exploratory runs

`pilot-01` exposed an interleaved statistics-write bug and is excluded. The
adapter now formats each record before one append write. `pilot-02` exercised
the first full matrix, using string-literal body probes, `debug=0`, and a function
cache that included registry crates. Its fre example hit an existing unrelated
dev-dependency build error, so fre is excluded from that run's comparisons.
The current fre consumer avoids those dev-dependencies without patching fre.

`debug=0` implicitly enabled post-link stripping on this Cargo version. On the
host, the extra binary rewrite materially affected warm measurements. Separate
instrumented experiments compared the system linker, LLD, and disabling stripping.
LLD was slower for the tested large binaries; it is not the default. The current
`dev-profiles-03` run keeps repository debug settings, uses new arithmetic edits,
and restricts function caching to workspace crates. Do not treat the difference
between these runs as an isolated cache speedup.

`profile.py` produces separate `-Ztime-passes` diagnostics. Its Cargo mode can
rebuild additional dependencies; those command wall times are not warm benchmark
samples. Rustc phase times can nest and must not be added indiscriminately.
The linker experiments also change final-crate arguments and are diagnostic
evidence, not replacements for the interleaved end-to-end measurements.

The current cache does not eliminate frontend work, MIR-to-Cranelift lowering,
object assembly, linking, or process startup. A high hit rate alone is not a
successful result. Adoption requires a useful reduction in the actual feedback
loop, including application/test execution, without weakened Rust checking.
