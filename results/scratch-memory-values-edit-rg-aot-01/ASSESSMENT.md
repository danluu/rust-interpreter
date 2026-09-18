# Private rg-aot full regression guard passed

All 132 commands preserve original assertions, expected incorrect-edit failures,
candidate/control bytecode identity and restored source. Median paired wall
candidate/control is **1.004840** (0.48% higher), CPU **1.008911** (0.89% higher).
A/A envelopes are 0.027329 wall and 0.006649 CPU. The existing regression
margins pass at **1.032169** wall and **1.015559** CPU. There is no incremental
speedup demonstrated here; the small measured increase is within the allowed
guard margin. Candidate/ordinary-native wall is **0.409691**.

The four passed full histories total 594 commands. Their closed checkpoint
admits Nushell only under its existing disk requirement. Complete parser
compatibility and the matched edited-parser comparison also remain before
adoption. Private source, test names, commands and raw reports stay in the
local private evidence; this result exposes aggregate measurements and hashes.
