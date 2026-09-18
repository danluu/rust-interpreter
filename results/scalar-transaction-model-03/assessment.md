# Private-store model qualified; native implementation is next

All 369 bytecode tests pass in debug and release, with 15 ignored observers per
profile. The added controls compare branched effects, overlapping aliases and a
non-idempotent increment followed by a fault. They also inspect the actual VM
memory immediately after a declined private attempt, before ordinary replay:
linear bytes, heap bytes, peak memory and active extent remain unchanged.

The four-command run exactly reproduces the previous census bytes: 168 bounded
store-bearing plans, 211 direct call sites, 138 block samples and one exhaustive
sample. The closure verifies 318 frozen inputs and 19 artifacts. Setup totals
62.80 seconds. No project guest or latency comparison ran, and production
admission still rejects external writes. Existing native unit tests ran; the new
transaction model published no native code.

The surviving coverage supports a separately qualified native prototype. Keep
bounded private store slots, checked original access ranges, same-address byte
forwarding and conservative alias declines. Commit only after successful Return,
where the existing Call bridge has no remaining fallible guest action. Native
controls must independently verify exact memory, faults, budgets, CFG paths,
register preservation and arena reconstruction before any real timing screen.
