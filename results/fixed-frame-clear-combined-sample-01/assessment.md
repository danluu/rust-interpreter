Three fresh owned executions of the combined runtime sampled 6,182 thread PCs. Clearing accounts for 165 samples (2.67%): 86 fixed stores and 79 loop instructions. The earlier profile had 14.81% clearing; these partial, perturbed windows are not a latency comparison.

Cursor accesses account for 1,044 samples (16.89%), with 667 (10.79% of all samples) accessing the remaining instruction budget. Every other cursor field is at most 1.20%. All stores and cursor accesses are tied to typed call layouts or compile-time layout assertions and exact code dumped by the sampled process. The previously parked budget-register experiment remains parked; this profile alone is not evidence that retrying it would meet an edit-latency gate.

All original assertions pass with 19,404,293,042 logical instructions, 151,962,257 resumable calls and no JIT declines. The next priority is resolving randomized-input controls in the combined-runtime comparison.
