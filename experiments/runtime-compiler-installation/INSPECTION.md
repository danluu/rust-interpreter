# First runtime metadata inspection

This is an unexecuted, read-only admission candidate for the separately declared
`owned-native-runtime-compiler-v1` policy. The installer at source `2c92ae36` passed
fourteen synthetic controls; that does not qualify these real inputs. This source
checkpoint runs no helper, compiler, test, archive scan, inventory or installation.

`inspection-plan-01.json` names the complete recorded inputs. `inspect.py` has one
metadata operation, using the existing supervisor and `owned_stage` canonical
600-second lock with the unchanged 8 GiB running floor. Its only writes are fresh
`.work/runtime-installation-inspection-01` metadata, receipts and retained source/
proof bytes. Failure remains a distinct failed attempt with no automatic retry.
There is no installation, cleanup, crate compilation or publication branch.

## Proposed components

| Role | Complete ordinary input directory | Destination in a future R |
| --- | --- | --- |
| Runtime | Qualified E `rustc-hir-capture-check-20260913/build/aarch64-apple-darwin/stage1` | sysroot root |
| Source | f9 installation `lib/rustlib/src/rust/library` | same library path |
| Support | f9 installation `lib/rustlib/aarch64-apple-darwin/bin` | same target bin path |

The paths are fully spelled out in the plan. Recorded counts are 64 runtime files,
3,644 source files and one support file, totaling 650,879,912 logical bytes. They
are expectations from retained inventories, not a current disk-space measurement.
The runtime already records both LLVM destinations, including target-lib LLVM;
no additional LLVM copy, D compiler, B private sysroot or rustc-dev is needed by
this proposed composition.

The exact runtime link `lib/rustlib/src/rust` is replaced by the ordinary library
provider. `lib/rustlib/rustc-src/rust` is explicitly omitted because this policy
provides no compiler/private source component. Both original link text and target
are checked. Neither link is followed for inventory or copying; SOURCE/build is
never recursively included through either source link. Existing ordinary source
scripts retain their actual read/execute permissions. Every provider file and
directory must match its original immutable ready-record stamps; files are
hashed, with no permission normalization or omission. Future installation removes
only write bits as the existing runtime policy specifies.

The prior f9 source comparison classifies 2,305 tracked library and 79 backtrace
files, plus 1,260 explicit distribution-only vendor/config files in 31 packages.
The inspector requires the tracked/backtrace hash maps and exact documented
omissions to equal E's recorded source maps. It rechecks complete vendored file
checksums, Cargo.lock package checksums and distributed `.cargo/config.toml` bytes.
The whole provider is retained, including distribution files; it is not replaced
by a partial compiler Git checkout. Its old compiler's source-remap capability is
not transferred to E.

The support directory must contain exactly its recorded `rust-objcopy`. The saved
CI LLVM member proof, f9 admitted object hash and both E/f9 LLVM hashes must agree.
The original CI archive is a provenance reference, not reopened or copied. Actual
Mach-O loads must validate with the complete proposed R layout. Auxiliary-tool
execution and stripping remain later native qualification requirements.

## Exact planned reads and children

Before live reads, retain and validate the frozen helper/import closure, the
materialized stage2 plan, E64 inventory, original native failure, complete replay
terminal, native archive manifest/summary, source record, f9 ready record, source
comparison and support proof. Stream-hash the existing 47,070,795-byte native
qualification evidence archive against its admitted hash; do not extract it.
Retain the 21 original and 14 replay child receipts and their exact stdout/stderr,
checking each against the archive manifest and its exact supervisor/helper/PID and
admission/start/finish associations. Every retained proof copy is independently
read back through an ordinary nlink=1 descriptor under the per-MiB guard. The original envelope remains failed;
its build, option and compiletest children plus the later complete direct replay
are the actual successful prerequisites.

The existing 135-input native source guard runs twice. Each pass uses five Git
children (HEAD, diff, tracked files, backtrace HEAD and backtrace tracked files),
checks the owned source marker/bootstrap configuration, and hashes the exact
recorded source membership. Its existing E runtime guard compares all 64 files
and both links. No old stage2 action or compiler build is called.

Read/stat/hash only the three proposed complete component directories, recording
ordinary modes, sizes, hashes, directory/link identities and nlinks. Recheck them
throughout admission and after all probes. Source and support subtree stamps must
also equal the saved immutable f9 record; the rest of the f9 compiler is not read.

The child dispatcher rejects every argv/cwd/environment combination outside the
frozen Git, compiler-probe, tool-selection and resolved otool allowlists. There are
25 proposed children in total:

- Ten existing read-only Git source-guard commands, five before and five after.
- `/usr/bin/xcrun --find otool`, followed by eleven `<selected-otool> -l <exact-image>`
  commands. The eleven logical image paths are exhaustively listed in the plan.
  Each selected tool/executable is hash/stamp bound before and after execution.
- Exact original E `bin/rustc -vV`, `--print sysroot`, and `-Zhelp` probes, with the
  sanitized environment in the plan and no version/loader overrides.

No native Rust program executes in this inspection. Identity probes refer to
original E, not a final-root R. The inspector validates the proposed relative
loader closure using `runtime_compiler.identity_for` and emits an immutable-input
*candidate* specification plus its tentative content key. Absolute/ambiguous or
missing native load edges fail admission; no load command is rewritten. There is
no successful ready record or claim that this candidate has been installed.

## Source capability and later sequence

The candidate deliberately omits `provenance.std_source_paths`. Ordinary matching
source files, the bootstrap configuration and f9's qualification do not establish
E-specific source diagnostic behavior. `std_mir_source_paths.compiler_sources`
must continue rejecting this candidate. Its existing `prepare()` also still
selects the complete-stage2 loader; this task does not change that selection.

A later explicit sequence must qualify final-root version/default-sysroot/options,
actual loaded driver/LLVM images, rustdoc/support tools, native compilation and
execution, raw uncalled type/borrow/const diagnostics, proc-macro/build-script
behavior, stripping and source snippets/virtual paths. E/R-specific native source
qualification must precede any v2 std-MIR admission. An installed content-derived
identity cannot silently acquire a capability: that requires a newly qualified
specification/installation or a separately designed explicit capability API.

Later runtime launcher selection must preserve the old complete-stage2 policy
and keep its default stable-CGU requirements separate. No launcher/std/tool
integration, exporter rebuild, performance claim, benchmark or holdout is part of
this inspection. Archived RUNTIME and EMBED worktrees remain unchanged.
