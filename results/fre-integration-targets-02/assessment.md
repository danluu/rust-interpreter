# Original fre integration assertions pass

All 52 original assertions across ten integration targets pass natively and in
the custom JIT. The launcher selects an exact Cargo test target and shares its
compatible dependency cache with the other integration targets. Target switching,
separate sidecars, the unchanged library route and strict uncalled type/borrow
errors were qualified in integration-targets-fixture-02.

The first real-target attempt incorrectly prefixed native test names with the
crate name. Those failed exports are preserved in fre-integration-targets-01;
the corrected driver passes native names unchanged. This run contains 20
commands, 40 output logs and ten preserved executed artifacts (15,848,273 bytes).
Their hashes and terminal receipts were checked. Compiler/runtime remain
`5b2330c/9637b0ac`; launcher source is `759bbbc`.

This is coverage, not edit latency or full libtest compatibility. Batches stop
at the first failure and share guest state with TLS resets between bodies. The
unfiltered native command's doc-test failure remains visible in
[its report](../fre-unfiltered-native-01/assessment.md). The existing library
replay separately covers 382 passing bodies and seven ignored bodies.

[Summary](summary.json) · [Actual edit pilot](../fre-integration-edit-01/assessment.md).
