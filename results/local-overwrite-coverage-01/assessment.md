Defer local-write elision. The typed proof finds 1,580 / 1,925 fully overwritten
writes, but their complete emitted operation spans cover only 1 / 1,651 and
2 / 1,439 generated-code samples. All three samples are data-transfer words.
This does not justify a runtime patch or timing screen. No guest benchmark,
interpreter change or artifact transformation runs.

Six controls pass in debug and release, including an independent 10,000-history
byte oracle with two initial-memory patterns. The oracle compares every read,
barrier memory snapshot and final byte after removing each candidate separately
and all candidates together. Controls preserve partial writes, copy source-before-
destination ordering, arithmetic widths, output aliases, unknown addresses,
assertion/call/fault barriers, independent region entries and bounded declines.

The exact saved native maps contain 20,160 / 23,541 regions. The proof declines
665 / 696 regions, representing 5,468,254 / 75,795 native bytecode operations
out of 15,847,599,048 / 13,360,844,452 in the separately bound profiles. No
executed function is omitted. Global work budgets are not exhausted. The
candidate counts include Store, Copy and fused FillBytes; all candidate operation
spans emit at least one word. Their 5,042 / 6,103 static words and 84,709,431 /
57,484,265 weighted emitted words include work that might remain. Neither is a
retired-instruction count or elapsed-time saving.

Setup takes 2.82 seconds; the two typed analyses take 1.84 / 1.64 seconds.
The coverage audit verifies 85 frozen inputs and 552 Git bindings, retaining
the original memory-partition qualification, raw maps, samples and artifacts.
The two short sample windows and full-test profiles remain different scopes.

The separate historical review also confirms that capacity credit already has
a qualified parked implementation. Do not recreate it. Next measure bounded
call-tree eligibility and its overlap with current native protocol samples
before considering a bridge between the tree and resumable calling conventions.
That bridge is a new design, not a repeat of the old standalone tree option.
