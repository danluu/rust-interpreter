# Partition actual small-memory instructions before the next runtime change

The adopted code's two saved samples place 686/1,651 and 388/1,439 generated
samples in coarse Copy/Load spans. Those include address resolution, checks,
transfers and result publication. Successor-only flushing passes its screen but
fails the full primary gate; do not retime it unchanged. Scratch forwarding and
the wider boundary-memory bundle remain possible components, not adopted code.

Start from the adopted ordinary emitter, with the rejected flush predicate
absent. Add disabled-by-default test-only per-word labels for Load, Store and
Copy of at most 16 bytes. Separate source/destination address materialization,
known local/shared/guarded frame addresses, tagged address-space selection,
bounds checks, readonly checks, host-address formation, memory loads/stores,
forwarded-value materialization, register input reads and register publication.
Keep large Copy, CopyDynamic, fused fills and native Call/Return outside this
selected partition. Labels must stop at each original operation boundary.

Three new controls cover dynamic pointers with/without heap addressing, known
frames, shared bases, captured/constant forwarding, odd widths, region boundaries
and excluded operations. Run all 412 bytecode tests in debug and release; nine
diagnostic tests are intentionally ignored. Existing execution/fault/budget tests
remain active. Use two Cargo workers and the existing owned shared build target.

Two explicit offline replays must reconstruct every original emitted word,
operation span, assertion and resume entry in both adopted captures. Observer
on/off must be identical, and every selected operation span must be completely
partitioned with no unclassified word. Do not publish executable code or run a
new guest sample. Then join the typed labels to existing exact logical profiles
and the same-process saved sample PCs; preserve all original input hashes.
Report excluded executed functions and ambiguous sample labels explicitly; no
missing work may silently count as zero. Weighted emitted words are not retired
instructions, and the two short perturbed samples are not timing measurements.

Use the shared benchmark lock with 45-second admission, 12 GiB initial build
headroom and 8 GiB before each child. Preserve original sources, assertions,
limits, artifact format, the 16 MiB default, peer work, the independent cleaner
and the paused goal. Choose any next mechanism only after this evidence. A
later runtime composition still needs strict/original-test qualification, a
fresh primary screen and all full adoption gates.
