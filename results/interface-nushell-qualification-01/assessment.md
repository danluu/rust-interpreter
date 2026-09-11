# Nushell generic-interface qualification

The public `Type::list(Type)` constructor was generalized to accept
`impl Into<Type>`. All fourteen original type-relation tests passed under native
Rust, baseline b2 and experimental resumable/persistent 78e60cdd. The original
wrong top-type relation failed in all three modes as expected. No test source
or expected result changed.

The one-cycle run verified nine primary commands, three independent Cargo checks,
one actual interface-edit pair and six matching custom artifacts. The independent
verifier reconstructed the pinned source states, tests and mode order from the
frozen JSON specification. All measured script hashes matched and the owned
source was restored. See [verification.json](verification.json) and
[complete report](summary.json).

The edited command took 11.172 s native, 5.147 s baseline and 5.517 s candidate;
the independent check took 4.223 s. This single pair is qualification evidence,
not a performance conclusion. Preserve the slower candidate observation. The
predeclared fifteen-cycle comparison follows both interface qualifications.

Native used root O0/incremental, 18 jobs and default libtest concurrency; custom
builds used four jobs, matched leaf inlining, the reusable std-MIR sysroot and
strict frontend checking. Build-script dependencies remained enabled. Cold
commands exclude toolchain/dependency fetch and std-MIR setup.

This covers a public constructor generalization within the selected package.
It does not establish whole-project, arbitrary trait-change or cross-crate
invalidation support, and does not change either failed primary token gate.
