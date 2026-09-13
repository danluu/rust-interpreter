# Descriptor I/O qualification plan (unexecuted)

This plan qualifies source checkpoint `b03aa904`, using the existing owned-stage
runner and supervisor. No command below has run for this checkpoint. It prepares
no benchmark, application build, compiler rebuild, std build or published toolset.
The implementation and fixtures remain frozen while this documentation is added.

## Fixed paths and environment

All commands use this working directory:

```text
ROOT=/Users/danluu/dev/rust-interp-guest-descriptor-io-20260913
WORK=ROOT/.work/descriptor-io-qualification-01
TARGET=WORK/target
PUBLIC=/Users/danluu/.rustup/toolchains/nightly-2026-09-08-aarch64-apple-darwin
STD=/Users/danluu/dev/rust-interp-semantic-reuse-20260913/.work/std-mir/bd27cc0f910e0c93a9a6cf088789ef526d36a8697a7717e08d7585f5d19467ef
PYTHON=/opt/homebrew/bin/python3
```

The selected Python must provide Python 3.11+ for the existing tomllib-based
dependency proof helper. Bind the logical executable's resolved path and bytes;
do not infer its identity from the Homebrew symlink alone.

These names abbreviate absolute paths in this document, not executable shell
assignments. The eventual reviewed command receipt expands every path. WORK,
TARGET and WORK/native must be newly owned directories; no old build target or
fixture history is reused. Use an explicit environment dictionary rather than
the current shell environment:

```text
HOME=/Users/danluu
CARGO_HOME=/Users/danluu/.cargo
RUSTUP_HOME=/Users/danluu/.rustup
PATH=PUBLIC/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin
RUSTC=PUBLIC/bin/rustc
RUSTDOC=PUBLIC/bin/rustdoc
RUSTUP_TOOLCHAIN=nightly-2026-09-08-aarch64-apple-darwin
TMPDIR=WORK/tmp/
LANG=C
LC_ALL=C
TZ=UTC
CARGO_TERM_COLOR=never
CARGO_NET_OFFLINE=true
PYTHONDONTWRITEBYTECODE=1
```

Create the owned temporary directory before children. Other environment keys are
absent, including compiler wrappers, Rust/Rustdoc flags, Cargo profile overrides,
incremental/build-target selectors, SDK/loader overrides, version overrides,
interpreter options and credentials. Preserve the repository's default release
profile and features. Cargo concurrency is two through the command line; the
Rust harness below explicitly uses two test threads. This is correctness
qualification, with no timing equivalence claimed for the instrumentation.

## Admission and input proof

Use `scripts/supervise_experiment.py` with fresh run ID
`descriptor-io-qualification-supervisor-01`; its child is a small fixed command
sequence calling existing `experiments/stable-cgu/owned_stage.py` helpers. No new
publisher, test framework or generic controller is needed. The outer supervisor
does not acquire a lock. The child writes its waiting receipt before acquiring
`workload_lock(Path('/Users/danluu/dev/rust-interp/.work/benchmark.lock'), 600)`.
Only the child holds the lock; none of the commands below reacquires it.

At admission require at least 16 GiB free: an 8 GiB setup allowance plus the
existing 8 GiB running floor. This allowance is a conservative admission budget,
not a measured target size or a filesystem quota. Retain `owned_stage.run`'s
five-second capacity observations and owned-process stop below 9 GiB. No peer
process or cache is controlled. A timeout or capacity/build/test failure remains
under its original IDs; any reviewed retry uses fresh IDs and retains its cause.

Before compilation, snapshot and hash the exact input files and record logical
paths, resolved paths, modes, byte sizes and existing stamp layout. Recheck before
each command and fully rehash at completion. The bounded inventory consists of:

- `Cargo.toml`, `Cargo.lock`, `rust-toolchain.toml`, every workspace crate file,
  both descriptor fixture/test files, both descriptor documents, the fixed
  sequence source and imported supervisor/ownership/identity helpers. Production
  files and the two fixtures must match `b03aa904`; record the documentation
  successor separately. Record every discovered Cargo config and ancestor config
  search. Require absence of configs for this initial recipe; any present config
  needs a concrete revised plan before Cargo runs, including recursive includes.
- Actual public rustc, rustdoc, Cargo and Python executable identities; public
  compiler-private/native std `.rlib`, `.rmeta` and dynamic libraries; the pinned
  rust-src Cargo.lock. Reuse existing `file_identity`, compiler inventory and
  `custom_cargo_libraries.library_closure(..., inspect=...)` primitives, with each
  actual otool child retained through the owned runner. Bind compiler/Cargo and
  later exporter/VM closure/search identities, plus the host platform. SDK/tool
  selection is recorded, not claimed as a hermetic SDK distribution.
- Cargo's actual `metadata --locked --offline --format-version=1` resolution for
  ROOT/Cargo.toml, selected local source files and resolved registry sources/
  checksummed archives. Reuse the existing public-build dependency inventory
  primitives. They are only input-proof helpers; the macro/worker/host-library
  publication qualification policies do not qualify this descriptor toolset.
- Existing STD/ready.json and all 26 listed metadata artifacts: exact owner,
  policy `metadata-sysroot-v1-release-backtrace`, target `aarch64-apple-darwin`,
  flags, ready hash, stamps, full artifact hash map and exact sysroot inventory.
  Recompute its identity key, and require its compiler version equals the actual
  selected rustc output. Preserve the original source/copy provenance in the
  ready receipt; the PRIMARY copy contains metadata, not a new source snapshot.
  Do not call `checked_std_mir` or any setup-on-miss path. Missing/mismatched
  prepared std fails admission without rebuilding or relabeling it.

Metadata children include exact `PUBLIC/bin/rustc -vV`, `--print sysroot`,
`PUBLIC/bin/cargo -Vv`, `PYTHON --version`, Cargo metadata and the closure probes.
Require compiler commit `cea272fa356e94bd2ee2cadf376630aa0683867a`, host AArch64
Darwin and PUBLIC as the native sysroot. Freeze actual version/identity outputs,
not expected binary hashes invented before the build. Metadata probes are not
counted among the three qualification commands or 17 nested fixture commands.

## Three qualification commands

Execute serially via `owned_stage.run`, with ROOT cwd and the fixed environment.
The first command exercises shared register, validation, inlining and JIT
visitors as well as the new module, so no redundant descriptor-only test run is
needed after a successful complete workspace suite.

```text
PUBLIC/bin/cargo test --workspace --release --locked --offline --jobs 2 --target-dir TARGET -- --test-threads=2
PUBLIC/bin/cargo build --release --locked --offline --jobs 2 --target-dir TARGET -p rust-interp-bytecode -p rust-interp-mir-export --bin rust-interp-vm --bin rust-interp-mir-export
PYTHON -B -m unittest discover -s tests -p test_descriptor_io_native.py -v
```

Require successful workspace summaries and report their actual totals, not a
historical count. Require these six fully qualified tests exactly once, each
`ok`, with none ignored or filtered:

```text
descriptor_io::tests::disabled_and_partial_programs_reject_before_guest_instructions
descriptor_io::tests::descriptor_encoding_registers_target_and_legacy_discriminants_are_checked
descriptor_io::tests::darwin::native_create_truncate_append_binary_empty_errno_and_getfd_agree
descriptor_io::tests::darwin::invalid_guest_memory_precedes_file_or_close_effects_and_drop_closes_owned_fds
descriptor_io::tests::darwin::guest_table_never_dispatches_unowned_host_numbers_and_resource_limit_is_a_trap
descriptor_io::tests::darwin::nonblocking_owned_pipe_exposes_short_write_and_eagain_without_retry
```

The second command builds the actual standalone binaries; unit-test executables
or an older installed toolset cannot substitute. Before the Python command,
record both binaries' hashes/stamps and complete loader closure. Freeze those
exact files through the native histories. Add only these variables for the
third command:

```text
RUST_INTERP_TEST_RUSTC=PUBLIC/bin/rustc
RUST_INTERP_TEST_EXPORTER=TARGET/release/rust-interp-mir-export
RUST_INTERP_TEST_VM=TARGET/release/rust-interp-vm
RUST_INTERP_TEST_STD_SYSROOT=STD/sysroot
RUST_INTERP_TEST_ARTIFACT_DIR=WORK/native
```

Require exactly two tests, `OK`, no skips, and both full method names from the
frozen suite. The suite produces 17 individual child receipts:

1. Twelve for native build, export, disabled refusal, and three create/append/
   truncate phases, each comparing the same native executable with interpreter
   and JIT. Raw return codes/stdout/stderr and actual file bytes must agree.
2. Five exports rejecting dynamic fcntl, unsupported F_SETFD shape, incorrect
   write width, incorrect variadic open mode width and incorrect close result.
   Each must have the frozen expected diagnostic and no output bytecode.

Those nested argv are exactly constructed by the frozen Python suite. In
particular, fixture compilation uses `-Copt-level=0`; export keeps metadata-only
`--emit=metadata`, the explicit prepared sysroot, and demand bodies/cache off.
The suite's own child environment deliberately retains only PATH/HOME/TMPDIR
plus fixed locale/timezone and those export controls. No launcher routes,
unsupported-call fallback, syscall retry or profile override is introduced.

## Retained evidence and limits

Keep each supervisor/command receipt, exact sanitized environments, owned PID/
parent/cwd/start/end data, all raw streams, copied source inputs, actual versions,
dependency and closure proofs, workspace summaries, each native/RBC artifact,
the three separate native/interpreter/JIT output directories and final file
bytes. Each phase's comparisons are assertions in the frozen suite; it retains
per-command raw receipts, not independent copies of every intermediate file.
Hash the test-produced
artifacts and restore/identity checks after completion, without overwriting any
failure. Archive compact evidence using the existing result style; do not include
the Cargo target or duplicate public compiler binaries. Actual tool binary
hashes identify this local qualification; they are not a fabricated publication
key. No assessment is passing until the real commands and proof checks pass.

These controls cover the opened-descriptor primitive on this Darwin host. They
do not demonstrate close-error fault injection, a host open returning 0/1/2,
descriptor-number path translation, arbitrary filesystem or FFI behavior,
guest standard streams, full std::fs, normal main/flush lifecycle, subprocesses,
native proc-macro execution or Cargo build-script interpretation. Native pipe
setup in one Rust test exercises partial writes/EAGAIN; it adds no guest pipe
support. Both engines share the checked descriptor dispatch. No benchmark or
Nushell latency claim follows from correctness success.
