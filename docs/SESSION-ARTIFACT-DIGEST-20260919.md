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
Actual saved parser verification, diagnostic attribution, tool composition and a
new changed-source primary remain pending. The8.6ms prior catalog phase is a
motivation, not a claimed command speedup. No experimental runtime is adopted;
the earlier unmeasurable and failed comparisons remain unchanged.
