# Persistent-register result

Source `d664bce` / tool `e89de7f8` reduces complete edited-command latency by
**23.6% paired for token and 4.2% for folded-trie** against the original
`b2aa6efe` baseline. CPU improves too. Token passes its original 20% target;
folded still misses 10%, so the combined primary gate fails. Keep native calls,
call stubs and persistent registers experimental and disabled by default.

| Workload | Native command | Baseline JIT | Persistent-register candidate | Median paired change |
| --- | ---: | ---: | ---: | ---: |
| folded-literal-trie | 1.634 s | 2.472 s | 2.373 s | −4.2% |
| token-phrase | 1.952 s | 6.482 s | 4.959 s | −23.6% |

Command columns are marginal medians over fifteen edited commands per mode;
change is the median within-edit candidate/baseline ratio. Paired child CPU
changes are −3.9% folded and −23.6% token. Median paired wall differences are
−101 ms and −1.515 s; CPU differences are −94 ms and −1.519 s. Both custom
versions remain slower than the native control on these workloads. These
results measure the complete native-call/register candidate against the original
baseline; they do not isolate register allocation's contribution by subtracting
separate historical experiments.

Folded execution medians are 1.553 s baseline / 1.452 s candidate, with Cargo/
export 0.868 / 0.852 s. Token execution is 5.094 / 3.576 s, with Cargo/export
1.293 / 1.291 s. Separate stage medians do not add to command medians.

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

The candidate passes 240 workspace tests in debug/release, ten CLI checks and
both original-artifact smoke checks. Seven held-out workflows and the broader
native/TLS/fre execution corpus have not been run on it. Existing pgrust,
Nushell, Ruff and private rg-aot evidence belongs to older tools; this result
does not extend that qualification to the new runtime.

Next inspect fresh samples of this exact tool. Remaining register traffic,
frame reservation/initialization and native/VM boundaries need separate evidence
before selecting another change. Keep the original gates. Frame lifetime work
requires a new byte-initialization/alias proof, as described in the
[source review](../../benchmarks/experiments/bounded-native-calls/FRAME-REUSE-REVIEW.md).

[Gate calculations](gate-evaluation.json) · [Final verification](final-verification.json) ·
[Folded report](../persistent-e2e-01-folded-literal-trie/summary.json) ·
[Token report](../persistent-e2e-01-token-phrase/summary.json)
