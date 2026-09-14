# Destination-readback repair: synthetic qualification

All **14 controls passed**, with no skips, on source
`2c92ae367f4e0e6e1eca06cee4eae100b3e9e531`. Raw unittest stderr reports
`Ran 14 tests in 0.325s` and `OK`. The added regression corrupts a copied driver
before the first output stamp capture and requires rejection before any compiler
probe or ready record. All files and probes in these tests are synthetic.

The predecessor's thirteen-control result remains unchanged in
`results/runtime-compiler-controls-01`; it predates this repair. Neither result
claims a real runtime installation, native compiler qualification or benchmark.

- Actual supervisor/helper/test: **41323 / 41328 / 41330**.
- Canonical admission: **1789345082.696852–1789345083.0905862**.
- Frozen input manifest: `a27ee512af71085e87bf1865bd5ed6255167ecc18d81a7e5b6b187b8f434f7bb`.
- Raw command receipt: `ce7c2ba102c18daf579cbc75c8780c7f78c9b8a626fd18764c1c444eeb43b841`.

`evidence.tar.gz` contains 21 exact source/control/launch/supervisor files plus
its manifest, including all eight frozen source snapshots. `manifest.json` maps
original paths to member names, hashes and sizes. Every member passed readback;
archive SHA-256 is
`2b952edf370620a0d5abf48802e45604229aa58ad671e06938051a25840b6459`
(29,558 bytes).

Archival ran under the canonical lock, supervisor/helper **45850 / 45853**, at
**1789345130.389754–1789345130.399174**. Its helper/input manifest and exact
launch/admission/terminal evidence are retained alongside the archive and bound
by `archive-execution.json`.

Only the source README was updated after archiving its tested bytes. The runtime
module and fourteen tests remain byte-identical to the passing source checkpoint.
The prior source commits and results were preserved without relabeling them.
