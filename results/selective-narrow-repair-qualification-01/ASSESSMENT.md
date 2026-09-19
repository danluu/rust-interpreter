# Strict and cache qualification

All121 expected outcomes pass using tool6c26c1c8. Original, edited and restored
Cargo sources retain strict checking; unreachable type/borrow errors and the
actual partially checked artifact are rejected before scalar execution. Native,
interpreter and JIT fixture outputs match. Automatic and explicit reuse caches
pass. Sourcef13370dc completed normally under50389/50392;19frozen inputs and
all command logs are closed. No project latency claim follows.
