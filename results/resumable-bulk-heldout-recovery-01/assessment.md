# Completed held-out cases after an interrupted run

Six original cases plus one fresh Nushell retry verify 588 commands, 105 edited pairs and 294 artifacts.
The original run remains incomplete; its partial records and failure are preserved separately.

| Workflow | Paired wall change | Paired CPU change | Above wall limit? |
| --- | ---: | ---: | --- |
| pgrust | -1.88% | -1.87% | no |
| nushell | +0.60% | +0.40% | no |
| rg-aot | -0.03% | +0.11% | no |
| forward-anchored-tls | -1.58% | -4.63% | no |
| pgrust-sha1-inline8 | -4.38% | -4.46% | no |
| ruff | -0.56% | +0.34% | no |
| nushell-type-relations | -0.86% | +1.79% | no |

All ratios compare fixed candidate 78e60cdd with original b2 within each edit.
Both original token primary gates remain failed. This assessment does not retain the runtime.
See [complete provenance and stages](summary.json) and [preserved failure](../resumable-bulk-heldout-failure-01/assessment.md).
