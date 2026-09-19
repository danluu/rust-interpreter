# Reuse the hash of immutable request bytes

An experimental session candidate removes the second SHA256 pass over each current
artifact. It owns the exact file bytes and computes their digest once. The request
binding and catalog both check that digest. There is no constructor accepting a
declared digest, and no mutable byte access. Decoding rejects trailing bytes;
all catalog identities and full Program validation still precede guest execution.
The ordinary feature-off catalog API still hashes its input. Strict compiler
checking, fresh guest/native owners, current limits and report reservation remain.

Source4bc2123c passes656Rust tests per debug/release profile (16ignored),33diagnostic
controls,10feature-off session controls and a default VM build. The exact unchanged
442Python/22skipped record is reused after source/log binding checks. All48servers
and92clients have terminal receipts. Supervision56222/controller56225; closed77522/77525.
Tests cover same-size changed artifacts, stale catalogs despite a valid current
request digest, malformed headers/entries, trailing/partial/invalid Programs and
recovery. The corrected template key v3 and65,536-op size tier are included.

[Qualification](../results/session-artifact-digest-qualification-01/summary.json).
Actual saved parser replay297defbe also passed:16suites,1,824invocations and
16,865independently verified hits. Supervision88307/88310 closed91948/91951.
Exact outcomes, wrong-edit failure text, fresh guests/current limits and kernel
CPU reconcile. [Replay](../results/session-artifact-digest-parser-client-01/summary.json).

The separate diagnostic replay3cb83f0e (92450/92453, closed5661/5664) passes the same
1,824invocations, with16,244observed hits and verification off for phase attribution.
For the five valid cached edits, median catalog validation is0.015ms versus8.602ms
in the previous diagnostic. Input total is30.151ms versus37.273ms. Actual-byte
read/hash12.575ms, decode11.358ms and full Program validation5.991ms remain.
These different-time diagnostic runs establish that the targeted duplicate phase
has gone; their total-time difference is not a controlled command-speedup estimate.
Worker assignment makes cache-hit counts unsuitable as an improvement metric.
[Attribution](../results/session-artifact-digest-phases-parser-01/summary.json).

Tool composition and a new changed-source primary remain pending. The8.6ms prior catalog phase is a
motivation, not a claimed command speedup. No experimental runtime is adopted;
the earlier unmeasurable and failed comparisons remain unchanged.
