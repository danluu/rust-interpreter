# Explicit demand-region candidate build

Expose --jit-demand-regions in the VM and Cargo launcher. Require full checking
and resumable JIT execution before execution; prepared owners keep this option
fixed. Selected-entry and isolated fresh/prepared workers receive the same
Limits value. This changes no compiler policy or bytecode cache dependency key.

Report cumulative published/declined region counts, eager admission fallbacks,
and charged plan/metadata capacities per owner. These payload counts exclude
allocator rounding, transient scratch, code and the separate resume tables;
they are not RSS. Prepared execution reports the owner's accumulated state.

Build from ROOT into the existing shared target, with two Cargo workers and two
unit-test threads. Require max(14 GiB, 8 GiB + twice allocated target size) free
before every Cargo command and retain the eight-GiB child floor. Never clean the
shared target. Run 637 workspace controls per profile (15 ignored), all 430
Python tests (408 pass, 22 skip), build the release VM, and reconstruct both exact adopted captures. Publish an immutable
composition with the exact adopted exporter/wrapper binaries under the tool lock.
No original-project command or performance claim belongs to this setup run.

Next run strict/cache fixture qualification with demand mode, schema-3 observer
controls and three original-project profiles against exact adopted controls.
Only then start the complete primary changed-source comparison.

The first production build exposed missing arbitrary-register liveness in the
three-pair-only representation. The corrected candidate keeps a dense bitmap or
sparse nonzero words (whichever payload is smaller), plus explicit exceptional
successors; fallthrough is implicit. Production emission and unit tests use
these same queries. The old graph remains solely a test oracle. Previous compact
storage estimates omitted these required queries and are superseded; remeasure.
