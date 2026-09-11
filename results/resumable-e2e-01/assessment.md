# Resumable native-call result

Source `e1bec3e` / tool `035ef708` reduces complete edited-command latency by
**10.6% paired for folded-trie and 15.0% for token** against the original
`b2aa6efe` baseline. CPU improves too. Folded passes its original 10% target;
token misses 20%, so the combined primary gate fails. Resumable calls and
persistent registers remain experimental and disabled by default.

| Workload | Native command | Baseline JIT | Resumable candidate | Median paired change |
| --- | ---: | ---: | ---: | ---: |
| folded-literal-trie | 1.881 s | 2.477 s | 2.198 s | −10.6% |
| token-phrase | 2.208 s | 6.641 s | 5.715 s | −15.0% |

Command columns are marginal medians over fifteen edited commands per mode;
change is the median within-edit candidate/baseline ratio. Paired child CPU
changes are −11.4% folded and −14.7% token. Median paired wall differences are
−253 ms and −987 ms; CPU differences are −271 ms and −955 ms. Both custom
versions remain slower than the native control on these workloads.

Folded execution medians are 1.531 s baseline / 1.261 s candidate, with Cargo/
export 0.891 / 0.869 s. Token execution is 5.081 / 4.119 s, with Cargo/export
1.415 / 1.461 s. Separate stage medians do not add to command medians.

All **168 commands** completed: 126 primary and 42 independent Cargo-check
controls. Thirty edited pairs and 84 custom artifacts were reverified. Paired
bytecode is identical, every recorded runtime flag agrees with its command and
launcher receipt, original assertions/test sources remain unchanged, and wrong
edits fail as expected. All five owned source pins and restoration were checked.
No samples were discarded. Both fre workflows retain cross-history artifact
layout differences; semantic equivalence and their cause remain unresolved.

Native uses root O0/incremental, 18 jobs and default libtest concurrency; custom
builds use four jobs and the frozen workload-specific settings. Package overrides
remain, so this is not a fastest-native claim. Instruction/allocation limits are
unchanged, including token's 150,000 allocation allowance. Toolchain/dependency/
std-MIR setup is excluded; OS caches were not cleared and unrelated work was
left alone. Only the original selected test batches were run.

The candidate passes 256 workspace tests in debug/release, twelve CLI checks and
both original-artifact smoke checks. Seven held-out workflows and the broader
native/TLS/fre execution corpus have not been run on it. Existing large-project
qualification belongs to older tools and does not extend to this runtime.

The previous persistent tree/stub experiment improved token 23.6% and folded
4.2% against b2. These separate runs suggest a tradeoff, but are not a paired
comparison isolating its cause. Next capture exact-code profiles of this tool
on both original artifacts. Diagnose native Call/Return work and remaining VM
transitions before selecting another implementation. Keep the original gates;
do not claim retention or a predicted saving from reduced native-entry counts.

[Gate calculations](gate-evaluation.json) · [Final verification](final-verification.json) ·
[Folded report](../resumable-e2e-01-folded-literal-trie/summary.json) ·
[Token report](../resumable-e2e-01-token-phrase/summary.json)
