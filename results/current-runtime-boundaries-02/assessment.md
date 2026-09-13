# Current runtime boundaries

All six commands and three original tests pass. Fresh controls and instrumented executions of the same integrated VM match exact logical instructions, peak guest memory and recorded entropy; no JIT compilation declines occurred. These use original-state artifacts from the completed changed-source histories.

| Test | Interpreted operations | Binary | Indirect calls | Allocation / deallocation / reallocation |
| --- | ---: | ---: | ---: | ---: |
| Token block boundaries | 6,774,341 | 4,842,143 | 1,025,947 | 885,372 |
| Token exhaustive semantics | 2,436,563 | 18,823 | 843,776 | 1,572,514 |
| Folded common offset | 75,284 | 157 | 33 | 74,906 |

The block-boundary profile changes the immediate priority: 4,842,143 of 6,774,341 interpreted operations are binary operations. Their rendered diagnostic labels show 2,421,047 wide left shifts, 2,304,975 wide ANDs, 116,119 wide ORs and two wide right shifts. The current typed JIT support match excludes those128-bit operations. Implementing these finite integer operations is a smaller first change than an adaptive indirect-call cache or an allocator bridge.

The exhaustive test still concentrates in indirect calls and allocator operations; the block-boundary result must not be generalized to it. Both original tests remain required in the end-to-end selection. Profiles are logical counters, not retired instructions, time attribution or a speedup prediction. Rendered operation labels identify investigations only; emitter implementation and correctness checks use typed bytecode.

VM-side lifetime allocation remains deferred: the prior screen increased both Cargo and VM stages, so moving its pass alone does not establish a win. The exporter-wide198ms cost is only part of that result.

The first census admission stopped after45s with zero commands while another workload held the lock. After a read-only check found the lock available, this distinct run executed the six previously outstanding commands. No successful test or timing was rerun to cross a gate.

Baseline tool: `49746a2218dbfdccacac0031f47e7a13b0440489c226979ff3374f6f899e09f9`.
VM SHA256: `2aea9015b2a02b340405e9824a050df4660c5646e2cfc2eec07f883a5234a867`.
Summary SHA256: `2994759ddec4b68da6ec88d70d3b234ddb6d3640e00de2130c291db7fc1f4f92`.
