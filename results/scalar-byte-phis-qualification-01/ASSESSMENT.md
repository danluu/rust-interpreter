# Strict and cache checks pass for byte phis

All 121 commands have their expected outcomes. Native-oracle, interpreter and
custom JIT fixtures agree across cold/reused artifacts, valid edits and source
restoration. Uncalled type/borrow errors stop execution; real partial-demand
artifacts cannot enter scalar execution. Automatic non-incremental cache mode
retains its checks. Closure binds 17 inputs and all logs to immutable 7d80e36f.
No project latency was measured. Proceed to exact original profiles and the
changed-source primary; main remains on df4006e0.
