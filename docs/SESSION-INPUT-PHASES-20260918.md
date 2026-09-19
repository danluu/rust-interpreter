# Session input costs after the cache-key correction

The diagnostic replay attributes most work outside the workers to reading and
checking the current29.46MB artifact. For the five valid cached edits, median
input processing is37.27ms; report serialization/write/hash is0.144ms. This is
elapsed diagnostic time, not CPU or an end-to-end speedup measurement.

| Current request phase | Cached median, ms |
| --- | ---: |
| Artifact read and hash | 12.163 |
| Artifact decode | 10.687 |
| Catalog read and hash | 0.055 |
| Catalog decode | 0.022 |
| Catalog validation | 8.602 |
| Program structural validation | 5.705 |
| Report reservation | 0.078 |

Code inspection shows catalog validation computes the artifact SHA256 again after
read_bound has just checked those exact held bytes. The catalog is only12KB, so
its own read/parse is small. This identifies a specific duplicate operation. It
does not justify trusting the digest declared by a client or catalog.

Each worker constructor is about15.7ms:6.8ms before ExecutionMetadata and8.9ms
inside it. Their intervals overlap. Ordinary emission/restore medians remain
29.8–38.9ms per worker with history; scalar preparation is2.8–4.2ms. These may
include verifier-independent diagnostic overhead and cannot be added to predict
wall savings. The size-tier policy skips its giant function before these counters.

Corrected source dafcd639 runs7745/7748 and closes9270/9274. All16saved suites and
1,824original invocations match, including exact wrong-edit failures.17,056hits
are observed with verification OFF for attribution; the preceding corrected
replay independently verified16,299hits. Worker assignment/history changes make
the totals unsuitable for a direct comparison. All phase sums, byte sizes,
constructor bounds and kernel CPU reconcile.

[Diagnostic result](../results/corrected-session-input-phases-parser-01/summary.json).
Next test an owned immutable artifact-bytes value whose digest is computed once
from its actual bytes, then used for both request binding and catalog validation.
No caller-provided digest may construct that proof; decoding, full Program checks,
selected-entry checks and strict Rust checking stay mandatory. Qualify malformed
inputs and current catalogs before another changed-source primary. Keep old
unmeasurable/failed comparisons, resource floors and acceptance gates unchanged.
