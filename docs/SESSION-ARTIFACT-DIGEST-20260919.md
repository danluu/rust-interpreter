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

The separate diagnostic replay3cb83f0e (92450/92453, closed5661/5665) passes the same
1,824invocations, with16,244observed hits and verification off for phase attribution.
For the five valid cached edits, median catalog validation is0.015ms versus8.602ms
in the previous diagnostic. Input total is30.151ms versus37.273ms. Actual-byte
read/hash12.575ms, decode11.358ms and full Program validation5.991ms remain.
These different-time diagnostic runs establish that the targeted duplicate phase
has gone; their total-time difference is not a controlled command-speedup estimate.
Worker assignment makes cache-hit counts unsuitable as an improvement metric.
[Attribution](../results/session-artifact-digest-phases-parser-01/summary.json).

Tool composition0df0d368 completed17757/17795 and closed20907/20912, preserving
byte-identical adopted exporter/wrapper. Candidate tool
66f56fdaa94e8ac7220acd6806da9c99dbc8e45cd67a52e381a39afc41390b46
uses the corrected cache key and qualified release binaries, observer disabled.
[Composition](../results/session-artifact-digest-install-01/summary.json).
The new changed-source primaryf50d99f8 completed47517/47520 and closed2787/2793.
All40commands preserve114original outcomes, exact paired artifacts, source restoration
and current limits; both strict controls reject before session sequence1 advances.

| Edited-command metric | Candidate / adopted | A/A envelope | Ratio + envelope |
| --- | ---: | ---: | ---: |
| Wall | 0.959340 | 0.040075 | 0.999415 |
| CPU | 0.933851 | 0.013129 | 0.946980 |

It passes the original gates, narrowly on wall time. Candidate/native wall is1.321684
and CPU1.248364: this workload is still slower than native Rust. Candidate/session-off
wall is0.994204, CPU0.990586; do not attribute the entire baseline gain to template
history or to digest reuse alone. All server kernel/startup/tail CPU and setup/teardown
wall are included. No regression limit or noise threshold changed.
[Primary](../results/cross-program-template-parser-screen-incremental-04/summary.json).

Next qualify the110-command full three-cycle parser guard and then run it with
these same binaries,15edited pairs and unchanged acceptance gates. Later project
guards remain required. The screen does not establish general runtime adoption. The8.6ms prior catalog phase is a
motivation, not a claimed command speedup. No experimental runtime is adopted;
the earlier unmeasurable and failed comparisons remain unchanged.
