# Split arena checks are parked

The split heap/linear pointer-check experiment is correct on the tested cases
but makes the token prepared suite 2.51% slower in both wall and CPU time.
All six token pairs regress. It fails the predeclared10% improvement screen;
do not retime it or run its conditional real-edit promotion benchmarks.

| Suite | Original tests | Median paired wall change | Median paired CPU change |
| --- | ---: | ---: | ---: |
| token | 12 | +2.51% | +2.50% |
| folded | 18 | −0.52% | −0.55% |
| pgrust | 4 | −1.21% | −0.99% |

All42commands pass, including one excluded warm-up pair per suite and six
measured alternating pairs. Two previously recorded entropy streams per suite
are completely consumed. Every original test preserves its output, identity,
instruction count and peak guest memory against its old qualified receipt.
There are no JIT declines. These are saved prepared-suite process measurements,
including startup; no compilation or changed-source workflow was measured.

Source `b635802`, tool `1db4b3e0`, passes363tests/profile (one ignored). Three new
tests compare scalar accesses and copies with independent Memory operations at
null, readonly, arena, width and overflow boundaries, and compare aliases and
budget/fault ordering against the interpreter. All prior tests pass unchanged.
[Host qualification](../native-address-checks-build-01/summary.json),
[complete paired measurements](summary.json).

The native samples correctly identified a substantial address-translation path,
but replacing its conditional selects with explicit branches was not beneficial.
This adds to the evidence against choosing small emitter variants from logical
instruction counts or isolated sample shares. Keep the implementation only on
`experiment/native-address-checks-20260912`; main retains the prior emitter.
Next strengthen seeded valid-program differential coverage requested in the
review, before further structural runtime work. Complete-suite semantics and
large-project edited-command controls remain adoption priorities.
