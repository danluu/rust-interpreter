# Direct HIR capture diagnostics

Two bounded diagnostics used the existing stage1 compiler at source `3d7ad828`, the byte-identical frozen fixture and the original HIRC environment with no `RUSTC_FORCE_RUSTC_VERSION`. Both compiler commands returned zero. Each emitted 24 `rejected-body-tree` records; neither produced a successful capture or cache hit. The first produced a native binary which was not executed. The second added `-Zunpretty=hir-tree` and retained its full 2,851,254-byte textual output.

The smallest child function has block/literal/root IDs 1/2/3, matching the reported S=1/E=4 interval. Its visible spans lie within the owner; the HIR dump does not expose Span parent metadata. This did not establish the failing subcheck or a fix. The original compiletest native qualification remains failed. No performance result is claimed.

All 22 child receipts and raw outputs, both exact plans/helpers/supervisors, frozen fixture and imported source bytes, and compiler/std inventory equality proofs are retained. All archive members were read back and verified. Four predecessor archives were verified and referenced through exact manifests, summaries and hashes without duplicating their payloads.
