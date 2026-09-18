Both saved captures reconstruct exactly with the adopted emitter: ordinary functions, scalar bodies and operation maps match their original native bytes. The observer executes no guest and publishes no executable code. The existing four Rust observer controls and two unchanged Python contracts were reused through exact source/record bindings. Two saved-capture reconstructions and one attribution command passed.

| Capture | Generated self samples | Small memory samples | Payload loads | Address-space selection | Bounds | Payload stores |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| block | 1561 | 605 | 247 | 154 | 77 | 89 |
| exhaustive | 1231 | 281 | 124 | 75 | 27 | 44 |

Payload loads still account for 247/124 samples; eight-byte Load/Copy operations contribute 158/88 of those. Source address-space selection in Copy contributes another 103/40 samples across its widths. These are diagnostic windows, not whole-program fractions, timing comparisons or predicted removable costs. All smaller categories and host observations remain in the reports.

One bounded gap in the adopted scratch cache is worth counting: Copy records its destination but not its source, and it only remembers eight-byte values. A test-only observer can count additional actual loads whose source bytes are still held in x9, including narrow Copy operations whose stores consume only low bits. Narrow Load results require zero extension and must not inherit that weaker Copy proof. Require post-address queries, exact-range alias invalidation and unchanged emitted code before choosing a production change. Existing address-space-selector candidates remain parked; do not rerun them unchanged.

The closure verifies 289 frozen bindings and 19 artifact bindings. Host setup/reconstruction takes 73.99 seconds; no guest latency result is implied.
