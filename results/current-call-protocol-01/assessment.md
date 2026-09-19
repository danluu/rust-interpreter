# Current call costs are split across several mechanisms

Three focused partition/link controls pass in debug and release. The offline
observer reconstructs all scalar leaves, complete ordinary functions, assertion
identities, resume entries and isolated transitions in four saved captures exactly.
All generated Call/Return samples reconcile, with zero ambiguous fine labels.
No new original guest executes and no machine code is published.

| Sampled part | ES8 exhaustive | ES8 seeded | Token block | Token exhaustive |
| --- | ---: | ---: | ---: | ---: |
| All generated samples | 797 | 609 | 1933 | 1429 |
| All Call/Return samples | 258 | 262 | 510 | 502 |
| Ordinary frame clear | 56 | 38 | 115 | 88 |
| Scalar padding clear | 14 | 37 | 18 | 12 |
| Call entry budget | 14 | 27 | 43 | 25 |
| Frame publication | 25 | 20 | 43 | 43 |
| Return dispatch | 27 | 24 | 25 | 29 |
| Ordinary argument source | 16 | 14 | 54 | 26 |
| Ordinary argument copy | 1 | 0 | 10 | 62 |

These are partial-window self-PC sample counts, not exclusive CPU timings or
predicted gains. The scalar argument capture/body dispatch samples are small;
redesigning that ABI alone is not the strongest present direction. Ordinary
frame clear remains large, but prior wider-clear and initialization candidates
already have closed negative results and must not be rerun unchanged.

A new narrow proof question precedes another implementation: the fixed ordinary
clear already proves when caller alignment/extent makes callee padding empty,
including retained padding from earlier calls. The scalar commit currently runs
the dynamic padding helper anyway. Determine exact typed coverage of that same
invariant for scalar sites, together with the redundant zero-budget entry check
that precedes their stronger whole-leaf budget guard. This would remove proven
empty work rather than optimize byte stores. It is a hypothesis, not yet a
runtime change or permission to reinterpret the parked short-tail screen.

Keep strict source checking, exact budget/fault/profile semantics and prospective
real-edit gates. Any eventual combined candidate needs its own recorded scope,
correctness qualification and unchanged original assertions. Source remains the
adopted runtime with test-only observation; current default is still df4006.

[Partition counts and sites](summary.json), [closure](closure.json).
