# Metadata-sensitive pointer equality

The exporter now lowers wide raw-pointer equality and inequality by comparing
both 64-bit words, then combining the results. The custom JIT can execute these
ordinary scalar operations. Address-only comparison remains a separate operation;
wide-pointer ordering remains explicitly unsupported. No VM or wire-format
change was needed. [Rust pointer-equality semantics](https://doc.rust-lang.org/std/ptr/fn.eq.html).

The new fixture passes **3,578 native differential/rejection commands** across
four optimization settings, inlining on/off and both custom engines. Raw-pointer
cases use both installed and metadata sysroots; Arc allocation cases use the
metadata sysroot because installed std omits a non-generic allocation body at
MIR0. The first attempt's missing-MIR failure is retained. Cases include equal
addresses with unequal full-width metadata, unequal addresses with equal metadata,
mutable pointers, null raw slices without dereferencing, str/nested DSTs,
trait-object aliases, and Arc value equality. The prior exporter rejects the
fixture; ordering still rejects on the new exporter.
[Focused checks](../wide-pointer-focused-02.json).

Fresh regression checks pass **23,502 native commands** and **674 repeatability
and native commands**. The four repeatability artifacts equal the prior retained
build. Bytecode/VM and launcher/audit/option sources are unchanged, so their
previous validation is reused explicitly.
[Regression checks](../wide-pointer-default-validation-01.json).

The new complete fre collection has **327 identical prior artifacts** and **62
blocked bodies**. All 62 now pass the former equality blocker and reach the
existing **10,000-instance function-expansion limit**. This does **not** add any
passing original tests. Coverage remains **242 native-matching, 78 runtime
refusals, 7 ignored, 62 lowering-blocked**. The 242 execution results carry forward
by identical artifact and VM hashes; no new audit-body replay was necessary.
[Collection](../lowering-audit-fre-wide-pointer-01/summary.md).

The 11-test forward-anchored workflow passes five real production refactors,
unchanged original tests, and an effective wrong-edit control. Prior/current
exporters use the same VM and MIR3 settings; bytecode is identical in all five
pairs. Edited command medians are native **2.259 s**, prior **1.658 s**, current
**1.560 s**. The current build wins 4/5 pairs, but shared-host and Cargo variation
is visible and there is no changed guest code or VM to explain a runtime gain.
Treat this as workflow qualification, not a pointer-equality speedup.
[Every sample and stage](../e2e-paired-fre-forward-anchored-wide-pointer-01/summary.md).

Retain the semantic fix. Leave the function-expansion limit in place while
prioritizing the 62 already-exported tests blocked by CPU-feature queries.
A narrow actual-OS query primitive is the next candidate; TLS registration,
unwinding and larger regex graphs remain separate limitations.
