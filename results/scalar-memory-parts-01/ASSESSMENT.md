# Small-memory costs in the fresh scalar captures

The observer reconstructs all 1,050/1,245 ordinary functions and 60/69 scalar
bodies from the two saved unprofiled processes. All original words, operation
spans, assertion and resume identities match with observation disabled/enabled.
Four Rust controls and two Python controls pass; no guest execution or executable
publication occurs. The closure verifies 280 input bindings and 23 artifacts.

| Selected Load/Store/Copy self samples | Token block | Exhaustive token |
|---|---:|---:|
| Selected operations | 776 | 370 |
| Data loads | 376 | 195 |
| Address-space selection | 203 | 81 |
| Data stores | 102 | 58 |
| Bounds checks | 61 | 25 |
| Other selected work | 34 | 11 |

The selected Copy spans (up to 16 bytes) contribute 451/216 samples. Their data
loads contribute 171/98, address-space selection 159/65, stores 57/28 and bounds
checks 52/21. No selected sample has ambiguous ownership. Larger and dynamic
copies, fused fills and Call/Return machinery are outside this fine partition.

These partial, perturbed normal-entropy windows neither establish a hardware
instruction count nor predict an end-to-end gain. The old exact profiles supply
static identity only. Already-failed general address-check, branch-selector and
scratch-Load candidates remain parked.

Next inspect an unmeasured case: consecutive scalar Copies that reload exactly
the same local bytes still held in x9. The older scratch observer queried only
Load operations. Observe availability after all original address handling and
before the actual Copy load; retain all alias, clobber, bounds and control-flow
invalidations. A census must reconstruct these saved bytes and quantify the
affected load subparts before a runtime implementation is justified.

The helper reconstructs only test-side metadata. Production compilation is
unchanged; this branch does not qualify an adopted runtime revision.
