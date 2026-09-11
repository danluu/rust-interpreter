# Independent custom worker counts

The workflow and corpus CLIs now accept separate baseline/candidate Cargo worker
counts, keeping shared defaults and native/check controls independent. New reports
record resolved custom counts; the verifier checks every executed worker option,
even when the independent check is disabled. Duplicate job options are rejected.
The new helper is included in frozen inputs and archive source provenance.

Qualification revalidates seventeen historical reports, containing 1524 commands
and 762 artifacts, with unchanged verification results. These workflows were
inspected, not rerun. Two false worker receipts are rejected, including one with
the independent check disabled. Fourteen workflow and four corpus CLI rejection
cases fail before resolving tools or creating workflow directories. Matching
explicit custom counts preserve historical semantics.

[Helper02](../worker-count-helper-02/summary.json) passes six configurations,
48 rejection checks and sixteen parser rejection cases, including JSON-serializable
argument metadata. [Archive07](../cache-archive-qualification-07/summary.json)
passes all 44 rejections, four coordinator cases and both older archive formats
with the added source dependency. No real compiler cache changed during those
fixtures. Actual project qualification with four/eighteen workers follows.

[Full integration evidence and exact source hashes](summary.json).
