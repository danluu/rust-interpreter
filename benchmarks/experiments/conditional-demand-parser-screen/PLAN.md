# Prospective conditional-demand parser primary

Candidate 4cdd305b692c / VM 54fb895b2c77 enables demand only for programs with a
function beyond the existing 65,536-PC analysis bound. Its exact build,
122-command strict/cache qualification, three eager small-program profiles and
three current-parser profiles must be closed before admission. The broad demand
candidate remains parked. This is a new policy and a parser-specific mechanism.

Run all 114 original gram_core tests in each of five arms: native, adopted
baseline df4006e0, its independent duplicate, conditional candidate, and fixed
historical parser anchor 4a1381c4. The anchor is the exact runtime used in the
closed prior full-parser guard; it omits scalar calls. All custom arms use the
same qualified exporter/wrapper, resumable/persistent execution, automatic
checked function cache and cached toolchain lookup. Only candidate requests
conditional demand. No type/borrow-check skipping or profile/entropy shim.

Use the established production parser edits: original, deliberately wrong
initial lookahead, five successive lookahead/range rewrites and restored original.
This is one complete eight-state history, 40 new commands, rotating all five
arm positions. Force Cargo incremental mode, two Cargo workers and two prepared
workers per custom invocation. Native libtest keeps its historical default
threading. Include full Cargo/build/test wall and child CPU cost. Every arm must
see changed source relative to its own previous command. Compare exact native
and custom test outcomes and checked artifacts/catalogs on every state, including
wrong edits. Original assertion files are frozen; restore production source.

Only the five successful edited pairs enter ratios. Require median candidate /
baseline wall plus maximum individual absolute A/A deviation < 1; CPU ratio <= 1
and CPU ratio plus its A/A envelope <= 1.05. This permits full histories, not
adoption. A failed gate with either envelope above 8% is unmeasurable. Preserve
all measurements; consider at most one fresh quieter screen in that case, never
splice pairs, automatically retry or disrupt another workload. A low-noise
failure parks this policy and cancels larger comparisons.

Qualify nine new screen controls and ten unchanged production-edit/native-outcome
controls first. Hold the shared benchmark lock. Require 14 GiB before admission:
6 GiB new cache/evidence allowance plus the unchanged 8 GiB child floor. This is
new prospective admission, informed by the completed three-cycle parser history:
its four caches retired 2.28 GB of compiler intermediates; the fifth arm adds one
custom workspace. Record free space before and after every child and preserve
all code, source, tool and terminal bindings. Do not reuse or weaken the older
24 GiB full-history reservation. Full histories need separate admission.
