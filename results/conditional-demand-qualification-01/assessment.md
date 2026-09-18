# Strict/cache qualification

Candidate 4cdd305b692c passes all 122 commands with the conditional-demand option.
Native, interpreter and JIT fixture outputs match. Off, cold and reused checked
artifacts agree; original/helper-edited/restored Cargo outputs are correct.
Unreachable type and borrow errors stop execution, including automatic cache
fallback without incremental compilation. An actual partial artifact is rejected
by conditional demand even when its size predicate would select eager mode.

The closed evidence verifies all raw command outcomes and 17 frozen inputs.
No changed-source latency benchmark is included. Proceed to the three original
small-program profiles and the current parser coverage comparison.

[Summary](summary.json), [closure](closure.json).
