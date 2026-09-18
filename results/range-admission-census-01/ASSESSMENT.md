# Defer smaller guarded ranges after measuring additional scope

All seven commands passed: five planner controls in each profile, three exact
native reconstructions, two ownership controls and sample attribution. Lowering
the diagnostic threshold from eight to four preserves every previously selected
proof and consumes exactly the same analysis work. Production selection remains
eight; no new guard or guest was executed or published.

| Capture | Additional groups | Accesses | Functions | Selected / generated samples |
| --- | ---: | ---: | ---: | ---: |
| Block | 43 | 195 | 35 | 14 / 1561 |
| Exhaustive | 59 | 264 | 48 | 0 / 1231 |
| Parser | 7 | 29 | 6 | 0 / 85 |

Nine block samples belong to cached_state; the other five are spread over three
regions. The original memory operations include payload and other work that an
entry guard would not remove, and the census does not measure guard hit rates
or overhead. These partial self-PC windows do not establish zero benefit, but
they do not justify another memory-check implementation or timing screen.

Keep the threshold and adopted runtime unchanged. Review remaining complete
native Call frame-initialization work, preserving all prior failed clearing
candidates and checking current emitted behavior before designing a new change.
