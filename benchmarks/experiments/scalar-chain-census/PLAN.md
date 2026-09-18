# Size scalar call-chain scope before designing a native bridge

Current scalar lowering admits only leaves. The old native-tree bridge kept
ordinary guest frames; this investigation asks whether bounded initialized,
confined direct-call DAGs can eventually become one scalar value graph.

Diagnostic admission keeps the existing 512-operation/register/frame and
0/1/2/4/8/16-byte boundary limits per function. Dependencies must already pass;
leaves must lower and emit through the existing scalar backend, offline only.
Parents need initialized and confined proofs with exact local argument/result
ranges, supported scalar opcodes and an acyclic reachable CFG. Reject recursion,
unknown effects, indirect calls, external pointer reads, and analysis exhaustion.
Bound expanded trees to depth4, 2048 operations/registers and4096 frame bytes;
count shared children separately at each callsite. No parent graph is emitted.

Four controls per profile cover local arguments/results and five independent
interpreter values, ordered duplicate calls, uninitialized inputs, external reads,
recursion/CFG cycles/depth/work bounds and unsupported boundaries/effects. One
typed token census and two existing attribution controls reuse the closed exact
Call/Return sample joins only after every Function hash and Call target matches.
Five commands total. No original-project guest, native publication or runtime
policy changes. Samples are partial scope, not speedups or removable instruction
counts. Parent native lowering, logical frame addresses/peaks, every original PC,
fault replay and resource guards remain obligations for any later implementation.

Hold the shared benchmark lock; use the sole ROOT target and two Cargo/test
workers. Build admission max(14GiB,8GiB+twice allocated target), child floor8GiB.
Freeze source/evidence, close every attempt, and preserve all original gates.
