The immutable candidate build passes 622 workspace tests per profile, with
15 explicitly ignored diagnostics, plus 407 Python passes from 429 discovered
tests (22 declared compiler/native skips). All four build/check commands pass.
Setup totals 116.15 seconds; no original-project guest or timing benchmark runs.

Candidate tool `cb47107b` contains VM `959dfd4f`. It preserves the adopted
exporter `cf4b3499` and wrapper `45bca4f2` byte-for-byte, copied from tool
`df4006e0`. That adopted tool and all existing installed binaries remain intact.
The closure verifies 491 source/retained bindings and 14 artifacts against
`66aec1c8`, including the installed candidate and both prior control histories.

The full build includes the corrected heap-free ABI case and all original
bytecode controls. The actual native census admits 392 functions, preserves
71 existing scalar bodies and covers 94 block samples. These observations still
establish no latency gain or runtime preparation/arena coverage on real tests.

Next run strict/cache negatives and original profiles. The later changed-source
comparison uses scalar Calls in both arms, with adopted tool df4006e0 as the
runtime control. Main retains that adopted runtime until every required gate
passes; the new tool is only an experimental candidate.
