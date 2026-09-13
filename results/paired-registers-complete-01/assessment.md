# Paired register-transfer comparison completed

All 462 original/wrong/edit/restored commands pass, 154 per case. All 426
frozen inputs remain unchanged and both project sources are restored.

| Case | Paired wall change | Paired CPU change | Wall A/A | CPU A/A | Gate |
| --- | ---: | ---: | ---: | ---: | --- |
| Token, 12 tests | −0.71% | −0.09% | 1.77% | 1.56% | Fail |
| Folded trie | −0.41% | −0.05% | 3.85% | 3.32% | Pass |
| Pgrust | +0.42% | −0.003% | 4.10% | 3.93% | Pass |

The primary component gain remains inside its A/A envelope. Both guards pass
the prospective maximum-ratio-plus-noise rule. The full token stack gains
11.85% wall and 13.59% CPU against the fixed anchor but remains 1.790× ordinary
native and 2.088× line-tables native. Keep this candidate experimental without
retiming. Smaller generated code did not establish a useful command gain.

Debug/release each pass 421 Rust tests; 131 Python checks, seven exact real
tests, nine suite commands, 203 strict native/cache checks and three current
profiles pass. Every profiled VM operation and native interval matches the
wide-operation baseline. The emitter retains both words and the same exporter.

Next count repeated same-address validation in typed saved profiles before
removing any check. This is an offline diagnostic, with no guest execution.
