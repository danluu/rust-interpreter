# Guarded ranges pass the complete changed-source comparison

All five predeclared gates pass across726 commands. The token primary improves
wall2.55% and CPU1.43% against the adopted custom runtime. Its incremental wall
gate passes narrowly against2.275% observed A/A. It is18.98% faster than the fixed
custom anchor in this comparison and still takes1.773 times ordinary native.
This establishes a bounded incremental result on the declared selections.

| Case | Commands | Candidate/adopted wall | Candidate/adopted CPU | Wall A/A | Candidate/native wall |
| --- | ---: | ---: | ---: | ---: | ---: |
| token | 154 | 0.974506 | 0.985721 | 2.275% | 1.772760 |
| folded | 154 | 0.999673 | 1.007893 | 0.530% | 0.935909 |
| pgrust | 154 | 0.999250 | 1.001410 | 0.813% | 0.830567 |
| rg-aot | 132 | 0.994551 | 1.000997 | 2.614% | 0.388598 |
| nushell | 132 | 0.988192 | 0.999165 | 5.598% | 0.618820 |

The other four cases pass regression guards without establishing useful
incremental gains. Pgrust selects four hashfn tests; Nushell selects14 original
type-relation tests. These are real project edit/build/test workflows, with
explicitly limited selection coverage. Private source, names and raw records
stay local; only aggregates are published. No general Rust-project speedup is
claimed and no unchanged-build timing counts as an edited observation.

Full03 retained594 completed commands before Nushell's pre-case disk refusal.
The separately qualified continuation audited that prefix, added only132
previously unstarted commands, then completed the final serialized audit:
8,999 unique case inputs verified, every source restored at its pinned revision,
all receipts intact, and all original controller/continuation inputs unchanged.
Supervisor79844 and controller79847 finish successfully at epoch1789299097.6966138.
Original lock/disk admissions and the offline profile-validator repair remain
recorded. No completed case, timing pair or screen was repeated to pass a gate.

The measured tool is02bd8087, VM4e9c9af6, retained exporterc1370fe6 and wrapper
cff204c5, compiled from sourcee4da187. The main compiler has newer qualified
observer/query-reuse work, so source adoption requires a separately identified
complete-tool composition and strict correctness checks. Reuse exact component
proofs and qualify changed-source exports; do not repeat this timing campaign.
The completed comparison freeze can now be retired for that integration while
preserving these manifests, receipts and exact source commits.

[Summary and audit digests](summary.json),
[full protocol](../../benchmarks/experiments/guarded-ranges/FULL.md),
[retained pre-Nushell refusal](../guarded-ranges-full-03-admission/assessment.md),
[Nushell detail](../guarded-ranges-edit-nushell-01/assessment.md).
