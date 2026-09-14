# Full pgrust hash history passed its regression gate

All 154 commands preserve original assertions, expected incorrect-edit failures,
candidate/control bytecode identity and source restoration. Median paired wall
candidate/control is **0.993862**, CPU **0.994779**. These small changes are
inside A/A envelopes of 0.014998 wall and 0.015793 CPU. Treat the candidate as
unchanged here; this is not evidence of a meaningful incremental speedup.

The existing regression margins pass: **1.008860** wall and **1.010572** CPU.
Candidate/ordinary-native wall is **0.846553** (15.34% lower). The three completed
cases total 462 commands. The checkpoint admits the private rg-aot guard next.
Nushell and complete/edited-parser qualification still remain before adoption.
This selection covers pgrust hash tests; it does not establish whole-parser
compatibility or full-codebase execution coverage.
