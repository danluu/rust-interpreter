# Full folded matching history passed

All 154 commands complete with the original assertions, expected incorrect-edit
failures, matching candidate/control bytecode and restored source. Median paired
candidate/control wall is **0.968919** (3.11% lower), CPU **0.975493** (2.45%
lower). A/A envelopes are 0.014842 wall and 0.008846 CPU; the existing regression
margins are **0.983761** wall and **0.984339** CPU. The held-out gate passes.
Candidate/ordinary-native wall is **0.918104** (8.19% lower).

This is the same qualified df4006e0 / VM 6ac4dd9e composition and the same fresh
three-cycle protocol as token. The two completed cases total 308 commands.
The serialized checkpoint revalidates both histories and admits pgrust next;
private rg-aot, Nushell, complete parser compatibility and the edited-parser
comparison remain before adoption. No completed case will be rerun.
