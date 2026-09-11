# Pgrust generic-interface qualification

The public `hash_bytes(&[u8])` API was generalized to borrowed
`AsRef<[u8]> + ?Sized` inputs. All four original hashfn tests passed under native
Rust, baseline b2 and experimental resumable/persistent 78e60cdd. The original
wrong-multiplier edit failed in all three modes as expected. No test source or
expected result changed.

The one-cycle run verified nine primary commands, three independent Cargo checks,
one actual interface-edit pair and six matching custom artifacts. The case JSON,
source states, selections, order and frozen scripts were verified independently;
the owned source was restored to its pinned revision. See [verification.json](verification.json)
and the [complete report](summary.json).

The edited command took 0.656 s native, 0.476 s baseline and 0.459 s candidate;
the independent checking control took 0.365 s. These are single observations,
not a performance conclusion. The planned fifteen-cycle comparison is still
pending. Controls used native root O0/incremental, 18 jobs and default libtest
concurrency, with four custom jobs and matched guest settings.

This qualifies one selected-package interface change and the integrated source/
receipt IO changes. It does not establish general trait changes, cross-crate
invalidation, whole-project execution or a pass of the original token gates.
