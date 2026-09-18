# Direct POSIX path check: inconclusive comparison

The comparison completed, but the candidate failed the adoption rule below:
only eight of twelve pairs improved for both wall and CPU time, against the
required ten. The production source and tests were restored to the baseline.
The exact candidate source and expanded tests remain beside this file and in
the [retained evidence](../../results/runtime-lookup-relative-01/README.md).
There was no repeat or replacement observation.

The baseline preserves `scripts/runtime_compiler.py` at `237510c3`, including
the previously landed ancestor-walking improvement. The candidate changes only
the absolute-path predicate in `relative()` from constructing a `PurePosixPath`
to testing whether the string starts with `/`. Every other path, manifest,
file-inventory, loader and source check remains in place. On the pinned Python
3.14 implementation, `PurePosixPath.is_absolute()` applies this same predicate
to its raw path. No path normalization or Windows interpretation is introduced.

The existing runtime-control suite adds empty and repeated-root paths,
backslash/NUL rejection, non-string inputs, POSIX-relative drive-like names and
Unicode slash/dot lookalikes. It remains an unfiltered 22-test suite.

The fixed comparison has one control process, two warmup processes and twelve
alternating baseline/candidate pairs using the real immutable runtime and
prepared standard-library installation. Both modules are imported in both
worker modes before the component clock. Every lookup must return the same
runtime/std keys and physical roots. Whole worker time is retained but is not
ordinary launcher time. Failed controls stop the comparison. All observations
are retained; there is no replacement, trimming or repeat-until-passing rule.

Before measurement, the adoption rule is: unchanged identities and all controls
pass; median paired wall and CPU differences both favor the candidate; at least
ten of twelve pairs favor it for each metric; and both execution-order strata
have negative median differences for both metrics. A failed timing rule is an
inconclusive or unsuccessful screen, not evidence to claim a speedup. No
application-build or holdout claim follows even from a passing component screen.

The canonical lock, bounded 600-second admission and 16/9/8 GiB capacity policy
are unchanged. Publication and the first Ruff diagnostic have priority. This
comparison ran once after the Ruff diagnostic released the lock. Its historical
freeze refers to the temporary candidate in the production source path; those
exact bytes remain in the archive. The live production file is the baseline.
