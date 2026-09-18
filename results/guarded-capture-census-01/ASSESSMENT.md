# Defer private external captures after counting their costs

All seven commands pass, including three Rust controls per profile, three exact
native reconstructions and three Python ownership controls. The original code,
entries, assertions and operation counts match. No original guest or executable
publication occurs. The four-slot model retains complete values after original
register facts expire while keeping every write immediate.

| Capture | Reuses | Captures / used captures | Source address/load words | Selected address/load samples |
| --- | ---: | ---: | ---: | ---: |
| Block | 99 | 88 / 67 | 198 | 15 / 1561 |
| Exhaustive | 99 | 88 / 67 | 198 | 0 / 1231 |
| Parser | 0 | 0 / 0 | 0 | 0 / 85 |

Only three functions contain reuse. Just 32 static reuses occur after the first
reuse of their capture. Replacing a guarded address plus payload load still needs
a value transfer, and capturing a producer adds work. These costs are not modeled
as dynamic timing. The 23 whole-operation block samples therefore overstate even
the 15 address/load samples; neither is a speedup estimate. Defer implementation.

Recent scope checks ruled out several new narrow mechanisms. Next qualify one
prospective composition of existing native indirect transitions, successor-only
spilling and checked readonly scalar leaves against the adopted scalar/scratch
runtime. Their isolated gates remain failed and no gains are summed. This is new
composed code, requiring complete fault/memory/profile and strict-check controls,
then the unchanged full-token changed-source primary before any larger histories.
Keep aggregate output changes, new captures and smaller range guards excluded.
