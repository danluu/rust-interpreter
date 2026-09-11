# Allocation-origin query qualification

The inspector finds the original IMMUTABLE static once and reports all three
requests: one materialization through a relocation and two cache hits, with
full originating function context. A second query retains six equal-content
allocations, including distinct mutable LEFT and RIGHT TLS identities and
addresses. These values are not coalesced by the diagnostic.

Queries exclude uninitialized padding and return no matches for an absent
allocation. Nine rejection checks cover artifact mismatch, invalid query size/
type, match/request/ancestry/report limits and repeated function identity. All
original execution-qualified traces, bytecode and seven input/source hashes
remain unchanged. No guest code or compiler cache changes. Supervisor 25399/
controller 25410 finished successfully.

The separate [actual CLI inspection](../allocation-origin-static-cli-01/summary.json)
returns the same one static and three origins. This qualifies a tool for the
pending Nushell literal diagnosis; it does not yet explain that history's
changed allocation sharing or establish a reuse key. See [results](summary.json).

Review afterward found that the output-size check counted compact JSON rather
than the indented final file and its source map. The small reports above did
not exceed the bound. The original two driver sources are preserved and hashed
in [source preservation](source-preservation.json). The corrected
[qualification02](../allocation-origin-queries-02/assessment.md) supersedes this
version's output-bound qualification.
