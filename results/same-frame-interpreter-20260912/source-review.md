# Same-frame loop independent review

No blocking concern. Every backing/frame transition exits the inner loop before
reusing the held safe views: Reset; direct/indirect Call; accepted native tree;
ordinary Return; root Return with pending callbacks; callback continuation and
completion. All exits are explicitly labeled. Other opcode arms may change guest
arenas or callback metadata but cannot resize host register/Frame backing.

The interpreter checks its budget before every inner continuation; transitions
rejoin the original outer check. Terminal Return succeeds at the exact budget.
JIT specializations still execute one fallback before returning to native-entry
checks. PC updates, per-op profiles and call-proof pc-1 lookup remain unchanged.

Existing explicit mixed-call/backedge profile counts (40 steps), every-budget
native-exit tests, register-stack growth/reuse, and TLS nested-call/reset tests
cover the affected paths. No concrete coverage gap identified. Moving the checked
register window ahead of the first PC fetch changes error order only for invalid
internal host-frame extents, ruled out by validated frame construction and checked
native continuation extents. No unsafe access or copied-frame writeback added.
