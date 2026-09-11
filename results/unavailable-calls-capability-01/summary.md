# Explicit unavailable calls and a new production-edit workflow

The opt-in `--trap-unsupported-calls` option adds **11 passing original fre tests**.
The strict frontend still checks types and borrows. Unsupported direct foreign
calls and the compiler's `catch_unwind` intrinsic become explicit terminal stops;
operands are evaluated first. No host function is called and no successful return
is fabricated. Unsupported Rust operations still reject export. Hashed call-site
metadata follows Cargo's selected artifact, including cached configuration reverts.

Of all **389** discovered fre tests, **242** have native-matching execution
evidence: **231 reused** with exactly identical bytecode and VM hashes, plus **11
fresh native/JIT comparisons**. Another **78** stop at unavailable calls
(62 `sysctlbyname`, 16 `_tlv_atexit`); **7 ignored** tests are not run; **62** still
fail to lower metadata-sensitive wide-pointer equality. Collection lowered 327
bodies, which by itself does not establish execution support.

[Collection](../lowering-audit-fre-unavailable-calls-01/summary.md),
[first 61 execution trials](../audit-execution-fre-unavailable-calls-pilot-01/summary.md),
[remaining 35](../audit-execution-fre-unavailable-calls-remaining-01/summary.md).
The earlier foreign-only experiment added no passing tests because lowering next
stopped at `catch_unwind`; that failed experiment remains recorded.

All 11 newly passing tests, including the exhaustive class/suffix differential,
now run in one build/test command after five cumulative production refactors.
The original tests stay unchanged, and every mode rejects a deliberately wrong
production edit. Cold commands use empty per-engine caches; tool bootstrap,
metadata-sysroot installation, downloads and OS file-cache coldness are excluded.

| First comparison | Median edited command (s) | Cold command (s) |
|---|---:|---:|
| Native | 1.523 | 6.918 |
| Interpreter | 5.677 | 9.360 |
| JIT, default MIR | 1.694 | 5.107 |

This reproduces the cold-fast/warm-slower tradeoff. The JIT wins only 1/5 edited
commands; its median paired difference from native is **+100 ms**. The slow fifth
native sample remains included. [All samples](../e2e-workflow-fre-forward-anchored-unavailable-calls-01/summary.md).

A separate paired run changes only the custom guest's MIR optimization level,
from explicit level 1 to level 3. The exporter and VM binaries are identical;
guest bytecode differs in all five pairs. Both use leaf inlining and strict
checking, independent caches, and the same original tests and production edits.
Native keeps its ordinary Cargo profile.

| MIR comparison | Median edited command (s) | Cold command (s) |
|---|---:|---:|
| Native | 1.671 | 6.788 |
| JIT, MIR1 | 1.739 | 5.310 |
| JIT, MIR3 | 1.308 | 5.437 |

MIR3 wins **5/5** edited commands against both MIR1 and native. Its median paired
saving versus MIR1 is **358 ms**, including **292 ms** in execution and **62 ms**
in Cargo. These are separate medians and need not add exactly. Cold execution
costs 127 ms more than MIR1. The measured virtual instruction count drops about
29%, and entries into native code about 51%. This is useful evidence for spending
some frontend optimization on runtime-heavy tests; it does not yet justify a
global MIR-default change. Five edits on a shared host are not confidence intervals
or whole-suite results. [Paired commands and artifacts](../e2e-paired-fre-forward-anchored-mir-01/summary.md).

The option passes **76 focused checks**, including cold/hot foreign and intrinsic
boundaries, actual inlining, argument evaluation, stale metadata, strict errors,
source edits and native controls. Fresh default checks pass 24 leaf, 71 SIMD,
79 audit, 99 launcher, 674 determinism/native commands across four MIR/inlining
configurations, and **23,502 native differential/rejection commands**. The four
determinism artifacts equal the prior retained build. The 88 bytecode tests are
inherited from unchanged bytecode sources and an identical VM; they were not
rerun. The earlier 23,502-command inline run belongs to build 67a3, not this run.
[Focused evidence](../unavailable-calls-focused-01.json),
[default validation](../unavailable-calls-default-validation-01.json).

Keep both unavailable-call trapping and leaf inlining explicit. Next implement
wide-pointer equality using both address and metadata, then repeat collection
and native comparisons. Actual CPU-feature queries and TLS destructor behavior
require further runtime support; their current refusals are not passing tests.
