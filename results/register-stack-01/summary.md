# Reusable guest register stack

Guest calls now append zeroed registers to one reusable stack and truncate it
on return. This removes one allocation and free per call while retaining
activation initialization, caller values, and the live-memory budget. Generated
code receives fresh storage pointers on every entry, including after growth.

The bytecode suite passes. New checks exercise register-vector growth, large
register indices in the JIT, caller preservation, zeroing reused storage, and
the exact live-memory boundary. The full native differential suite also passes;
its detailed records are preserved in summary.json.

Three serial, uninstrumented repetitions reused exactly the same bytecode
artifacts before and after the runtime change:

| Artifact | Previous JIT execution process | Reusable register stack |
|---|---:|---:|
| Default MIR, final production edit | 12.619 s | 9.746 s |
| MIR level 3, original source | 6.014 s | 4.841 s |

These timings include VM startup, bytecode decoding, JIT emission, and execution.
They exclude compilation and are diagnostic runtime comparisons, not development
workflow results. The [full production-edit comparison](../e2e-workflow-fre-word64-mir3-arena-01/summary.md)
with MIR level 3 measured 5.731 s JIT, 18.017 s interpreted, and 2.081 s native.
That comparison includes both the MIR setting and register-stack change.
Both artifacts retain all twelve original exhaustive tests. Every repeated
execution returned success with unchanged instruction counts. The two rows use
different source states, so compare each row only with its own previous result.
