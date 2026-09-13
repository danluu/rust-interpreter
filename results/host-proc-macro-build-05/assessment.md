# Macro tool build and publication qualification

The same public-compiler toolset `4dd88495a41b36ba96c8784e2bf82f77de0be5b185ff408e910fdb9e0218ddc1` passed all eight required commands and
was published into both recorded owners. There is no performance result here.

Rust: **479 passed, one existing ignored test** (`jit::local_memory_tests::observe_local_forwarding_in_original_artifact`), whose retained
reason is “Explicit typed census of saved real bytecode; requires artifact paths”. Python: **3 launcher contracts, 24 screen contracts,
and all 3 real compiler histories passed**, with zero skips. The histories cover
uncalled errors, macro cfg/debug/overflow behavior, Cargo host macros and declared
file inputs, generated errors, fresh edits/restoration, and selected guest
bytecode parity. Source, actual commands/output, native/VM execution records and
the shared std receipt are retained; assertions are the frozen fixture's.

Plan03 failed on a registry layout assumption; plan04 passed that inventory and
failed on a logical loader-path validation mismatch. Both stopped before any of
their eight qualification commands. The initial missing `.work` admission failure
is also retained, including its unavailable-PID limitation. Plans01/02 remain
unexecuted. The fixes were qualified by five inventory tests, five loader tests,
and replay of all eight saved rustc inspection records without new inspector
processes. The prior 21-test archive is referenced by exact hash and was fully
reverified; it has not been overwritten or silently replaced.

Plan05's supervisor16668 completed in 74.487s,
including the build, tests, inventories and publication. This is setup duration,
not a warm build or an improvement estimate. Release debug level1 and the pinned
public compiler/Cargo identities are recorded. No custom compiler/Cargo or other
optimization policy was combined with the macro qualification.

`evidence.tar.gz` contains 1502 logical files in 537 physical
members. `manifest.json` maps every logical name to an exact archive member,
source path, size and SHA-256; identical bytes are stored once. Both owner
publications are revalidated using only reconstructed archive bytes with the
shared pure validator, including full publication input guards. Every archived
hash was checked after compression. Binaries/caches are not copied into Git.
The publication-time identities cover the actual three binaries, compiler and
Cargo, resolved non-system loader closures, platform assumption, dependency
archives/source files, effective configuration and prepared std artifacts.

Reproduce into a new output directory with `python3 -B
benchmarks/experiments/host-proc-macro/package_build.py --assessor-root
/Users/danluu/dev/rust-interp-owned-screen-assessment-20260913 --output <new-directory>` while the retained evidence remains available.
This packager executes no compiler, test, inspector or benchmark.
