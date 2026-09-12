# Saved real programs: bounded call specialization

After the complete debug/release qualification in SPECIALIZATION.md, transform
the original full token, folded-trie and pgrust test artifacts retained by
suite-profiling-real-01. Do not use the globally folded variants. Preserve the
original artifacts and record exact input/output hashes. Run a separate CLI
process to repeat the typed transform and compare every serialized byte.

Report clone count, redirected static sites, body reductions, analysis work,
encoded growth and offline transform time. These timings only diagnose likely
compiler cost; they are not an edit/build/test measurement. There is no dynamic
profile input to the transform and no exporter integration in this step.

If clones are produced, replay all original native assertions on the exact
baseline VM with the candidate artifacts and fixed entropy, alternating three
pairs per full suite. Original test catalog IDs and names must remain unchanged;
only its artifact digest may change after exact verification. Instruction
counts may change across artifacts but must repeat within each artifact. Require
identical per-test outcomes, memory peaks and consumed entropy. Retain the
existing full-suite native receipts as the semantic reference. Report runtime
and analysis cost separately; do not claim an end-to-end gain or adopt from it.

Use the existing 4 GiB floor for these offline operations and small evidence
files. No Cargo workspace cache is created or deleted. A successful diagnostic
still needs strict Rust edit/invalid-program controls and the real changed-source
gates in NEXT.md before integration can be considered qualified.
