# Cross-region facts: small measured coverage, one explicit exclusion

The offline extension passes 457 workspace Rust tests per debug/release profile,
including eight new CFG/alias/boundary tests. Eleven executable commands run
three typed censuses, one legacy-mode equivalence check and seven rejection
controls. No guest program is executed; the old CLI report is byte-identical,
invalid inputs create no report, and an existing output remains unchanged.

| Profile | Recorded fixed-address accesses in admitted functions | Additional in-frame opportunities | Of those, Copy addresses | Declined functions |
| --- | ---: | ---: | ---: | ---: |
| token block | 6,217,357,920 | 1,794 | 0 | 1 |
| token exhaustive | 4,638,621,834 | 15,106 | 15,096 | 1 |
| folded | 1,615,956,498 | 2 | 0 | 0 |

Every additional opportunity is a write. The earlier same-register census
excluded Copy; this census includes both fixed Copy endpoints. Counts compare
typed whole-CFG must-facts from unknown entry registers against the existing
region-local folding model. All branch successors participate; conflicting
joins, skipped definitions and unknown outputs remain unknown. These are
logical access opportunities, not emitted instructions or predicted time.

Both token profiles exclude regex_automata::nfa::thompson::Builder::build under
the declared analysis/storage limits. Its 86,836,280 and 378,834 recorded native
operations are 0.548% and 0.00284% of their respective totals. Counting every
one as two eligible fixed addresses gives conservative upper bounds of
173,672,560 and 757,668 unmeasured opportunities. They are not treated as zero;
neither operation fraction bounds elapsed time. The folded analysis is complete.
The follow-up coverage audit reads already typed-validated, hash-matched saved
profiles. Its first lock admission timed out without reading profiles; the
completed audit ran once after the peer released the shared lock.

Park cross-region local rematerialization as the immediate candidate. Its
observed coverage is tiny, and a production implementation would additionally
need to justify all native entry states, not only normal function entry.
Broader constant traffic and excluded-function precision remain unmeasured.
In admitted functions, the largest unknown-address counts include SipHash
rounds (118.6M/115.7M in the block test), regex determinization and sort/scan
helpers. Next count related pointer-range groups within native regions. Any
future group guard must fall back to original checks on guard failure, preserving
partial writes, fault ordering and logical budgets. No guard removal follows
from this census, and the failed checked-address screen will not be repeated.
