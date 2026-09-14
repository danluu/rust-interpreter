The diagnostic read-only scalar model passes 24 controls in each profile:
13 existing proof controls, five existing scalar-IR controls and six new read
controls. The new controls execute 282 reference cases per profile, preserving
values, original-PC counts, padding, conditional paths and fault order. Native
emission explicitly rejects the new Read node. No original-project guest runs
and no executable code is published.

The bounded scan admits 395 complete plans with external reads, with 414 direct
callsites. It uses 3,085,956 of 256 million proof work units without exhaustion.
Current block samples cover 42 Call/Return transitions and 53 body samples
(42 operation, eight flush, three budget), including nine frame-clear samples.
The exhaustive capture has zero coverage. These are partial perturbed coverage
observations, not removed work or a predicted speedup.

The largest observed opportunities are two regex state lookups (31 / 20 total
samples), a tag matcher (16), and an eight-byte vector load helper (10). Other
pointer-reading functions are rejected once their external writes or further
unsupported behavior is examined. The 84-sample first-decline category from the
preceding census was therefore only an upper bound.

The read-only proof allows only bounded reads and requires every write to
resolve inside the virtual frame. External effects and nested calls remain
rejected. Unused reads remain live because they can fault. A checked callback
models private failure/replay for fresh-frame and padding overlap; no production
transaction uses that callback. Existing production admission stays unchanged.

The closure verifies 314 source/retained bindings and 27 artifacts against
`6761f5e8`. Controllers require that diagnostic source. Next implement a bounded
native prototype with exact linear/heap read checks, original low-usize address
semantics, preserved live ABI registers, and ordinary-call replay before commit.
The saved pre-Call linear length can conservatively exclude the complete fresh
callee frame and padding. Check native emission coverage and differential
correctness before any changed-source screen. A native or end-to-end speedup is
not established by this census.
