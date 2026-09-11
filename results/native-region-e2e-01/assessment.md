# Ordinary-region native Call result

Source `26833c3` / tool `2f31c6a0` reduces token command latency by 19.3% paired,
but folded regresses 1.4%. **Both original performance gates fail.** Keep the
native-call options experimental and off by default. Next profile this exact
candidate to locate the remaining runtime cost before another implementation.

| Workload | Native command | Baseline JIT | Native-region candidate | Median paired change |
| --- | ---: | ---: | ---: | ---: |
| folded-literal-trie | 1.626 s | 2.509 s | 2.541 s | +1.4% |
| token-phrase | 1.958 s | 6.610 s | 5.334 s | −19.3% |

Command columns are marginal medians over fifteen edited commands per mode.
Change is the median within-edit candidate/baseline ratio, not the ratio of
marginal medians. Original targets remain −10% folded and −20% token against
b2aa6efe, with CPU improving too. Paired child CPU changes are +0.9% folded and
−19.2% token; median paired wall differences are +35 ms and −1.276 s. The token
result is close to its target, but that does not excuse the missed folded gate.

Folded execution medians are 1.569 s baseline / 1.604 s candidate and Cargo/export
0.869 / 0.880 s. Token execution is 5.197 / 3.959 s and Cargo/export 1.317 /
1.299 s. Separate stage medians do not add to command medians. Native completes
both selected workloads substantially faster than either custom version.

All **168 commands** completed: 126 primary and 42 independent Cargo-check
controls. Thirty edited pairs and all 84 custom artifacts were reverified;
corresponding engines received identical bytecode. Original assertions/test
sources and wrong-edit failures were preserved. All five owned project pins
and tracked-source restoration were rechecked. No samples were discarded.
Cross-history artifact layout differences persist in both fre workflows;
semantic equivalence and their cause remain unresolved.

Native uses root O0/incremental, 18 jobs and default libtest concurrency; custom
builds use four jobs and frozen workload-specific MIR/runtime flags. Package
overrides remain. Instruction/allocation limits are unchanged, including token's
150,000 allocation allowance. This is not the fastest native configuration.
Toolchain/dependency/std-MIR setup is excluded; OS caches were not cleared and
unrelated host work was left alone. Only the named original test batches were run.

The candidate passes 231 workspace tests in debug/release, seven CLI checks and
both saved real-artifact smoke checks. The smoke shows that ordinary Call stubs
execute millions of times and reduce host JIT entries considerably, while code
size increases. Those counts do not isolate CPU costs. The next diagnosis samples
fresh owned executions of this exact binary; older VM profile percentages cannot
be transferred to its new call boundary.

The seven held-out workflows and broader native/TLS/fre execution qualification
were not run on this candidate because the primary gates failed. They remain
required before retention. Existing nine-workflow baseline evidence includes
pgrust, Nushell, Ruff and private rg-aot; this experiment does not extend their
qualification to the new runtime.

[Gate calculations](gate-evaluation.json) · [Final verification](final-verification.json) ·
[Folded report](../native-region-e2e-01-folded-literal-trie/summary.json) ·
[Token report](../native-region-e2e-01-token-phrase/summary.json) ·
[Profiling protocol](../../benchmarks/experiments/bounded-native-calls/PROFILING.md)
