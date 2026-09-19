# Current ES8 execution cost

All four original-test executions completed and the six-command diagnostic
campaign is independently closed. The restored original artifact comes from the
matched32-command ES8 edit history; the engine remains the adopted df4006 VM.
There is no new runtime implementation or adoption.

| Captured generated-code samples | Exhaustive test | Seeded/window test |
| --- | ---: | ---: |
| All assigned samples | 797 | 609 |
| Call transitions | 202 | 207 |
| Return transitions | 56 | 55 |
| Copy | 149 | 115 |
| Load | 96 | 50 |
| Flush | 66 | 43 |
| Budget | 46 | 17 |

All generated samples were assigned to verified same-process code spans. These
are partial, perturbed windows, with ordinary entropy. Shares describe observed
locations; they are not removable fractions or speedup forecasts. Logical
profiles are separate executions and provide static identities for the samples,
not comparable dynamic counts across runs. Profiles reported10.633B/8.751B
logical operations, with only962,375/49,229 interpreted operations, and zero
declined JIT functions. Each profile's per-PC totals reconcile with VM statistics
and its complete emitted code/map reconstructs exactly.

Call/Return spans account for258/797 and262/609 generated samples. The hottest
calls are in ordinary iterator functions: Range::spec_next, Iterator::fold and
map_fold closures. Calls from Range::spec_next to the generic unchecked-add
precondition checker account for32/64 samples. That checker already uses the
scalar backend: its current unprofiled body is124bytes, while the caller retains
the transactional Call protocol. Removing the assertion is not an optimization
option. The sampled native protocol, including eligibility, capture, commit and
fallback, needs a finer partition before selecting a change.

Calls to Vec::extend_trusted's closure account for40/55 samples, and fold's
map_fold call for29/43. This workload therefore adds useful call-chain evidence
beyond the token suite. Earlier capacity-credit, whole-call expansion and scalar
effect prototypes remain parked with their original verdicts; these samples do
not retroactively approve them or justify another unchanged timing run.

Next use these retained captures to separate resource eligibility, argument
capture, dispatch and commit costs at scalar and ordinary calls. Consider a new
generic mechanism only with meaningful current scope and explicit preservation
of budget tails, errors, aliasing, zeroed padding, peak memory and fallback.
Any implementation must subsequently pass real changed-source measurements and
the other original-project guards. No fixture substitution, source assertion
change, new compiler build or foreign guest backend was used here.
