# Empty scalar entry work: defer runtime changes

Six commands completed and were independently closed: the two model tests in
both debug and release, followed by four typed metadata captures. No guest ran
and no executable code was published. The production runtime remains adopted
fca687eb; the inconclusive short-tail candidate remains parked.

| Capture | Scalar sites | Statically empty sites | Empty padding samples | Unproved padding samples | Common budget samples, upper bound |
| --- | ---: | ---: | ---: | ---: | ---: |
| ES8 exhaustive | 79 | 38 | 0 | 14 | 2 |
| ES8 seeded | 78 | 38 | 0 | 37 | 6 |
| Token block | 427 | 121 | 0 | 18 | 11 |
| Token exhaustive | 532 | 149 | 1 | 11 | 6 |

All transition samples were resolved without ambiguity. The existing static
caller alignment/extent invariant proves many sites empty, but only one sampled
padding PC across all four captures qualifies. The redundant common entry-budget
check has similarly limited scope; its counts are an upper bound because the
ordinary fallback still needs the check. Neither subset justifies a runtime
candidate or an end-to-end timing screen on this evidence.

The hot ES8 site is caller245/pc70 -> callee10, accounting for12/14 and37/37
unproved scalar padding samples. Both frames align to16 bytes, but the caller's
extent is120 bytes. A fresh caller therefore needs8 bytes of padding; an earlier
call may already have retained that padding. Static frame alignment alone cannot
distinguish these histories. Do not infer an empty-range frequency from the PC
samples or treat these counts as a predicted speedup.

Next investigate typed control flow and memory-end history at current hot call
sites. A stronger exact-extent proof would be a separate mechanism with its own
model, joins/backedges/unknown effects, scope evidence and prospective screen.
It must preserve alignment overflow checks, fault order, memory/peak semantics,
logical budgets, profiles, fallback and strict frontend checking. No unchanged
retry of the parked short-tail candidate is authorized by this assessment.
