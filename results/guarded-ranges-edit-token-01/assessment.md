# Guarded-range full primary

All154 commands pass their expected outcomes with12 unchanged original tests,
three original/wrong/five-valid-edit cycles and final source restoration.
Baseline/duplicate/candidate bytecode and catalogs match for each state. Only
the15 valid edits enter the paired results; no screen pair is reused.

| Measurement | Median paired candidate/control ratio |
| --- | ---: |
| Adopted runtime wall |0.974506 |
| Adopted runtime CPU |0.985721 |
| Fixed anchor wall |0.810233 |
| Fixed anchor CPU |0.814141 |
| Ordinary native wall |1.772760 |
| Native line-tables wall |1.963137 |

Wall improves2.55% and CPU1.43% versus the adopted runtime. Observed A/A is
2.275% wall and1.730% CPU, giving wall margin0.997252 and CPU margin1.003025.
The primary passes its frozen gate, narrowly for incremental wall improvement.
These are engineering margins, not confidence intervals. Fixed-anchor gains
include previously adopted work; the candidate still takes1.773 times ordinary
native Cargo for this selection. Ratios are medians of individual edited pairs,
not ratios of independently calculated arm medians.

The controller proceeds to folded matching, pgrust, private rg-aot and Nushell.
All four guards and the final serialized source/input audit remain mandatory.
This primary result alone does not adopt the runtime or establish a general
Rust application speedup. No completed command was repeated; two earlier
controller attempts expired before their first case was admitted.

Case controller42962 ran under supervisor42957/controller42960 of full03.
Minimum recorded free space was27,383,140,352bytes. The exact case plan,
records, transitions and space digests are in summary.json.
