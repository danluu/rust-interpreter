# Independent Cargo compiler-info-cache screen

`--candidate-policy cargo-info-cache` compares the matched stock and patched
Cargo executables with one public pinned compiler and one exporter/VM tool key.
Both `--baseline-tool-key` and `--candidate-tool-key` must name that same tool.
`--baseline-cargo-key` selects stock Cargo for A and its independent duplicate
A′; `--candidate-cargo-key` selects the patched Cargo for B. Custom compiler,
stable-CGU and retention policy switches are not part of this comparison.

Before any project command the screen validates each owned Cargo installation,
its dynamic-library closure and copied qualification/source provenance. The
pair must have different actual Cargo binary hashes, identical compiler/build
settings/features/profiles, one shared passed qualification and exactly one
different production source input: `src/util/rustc.rs`. Source identities alone
or differently built distributed/local Cargo binaries do not qualify a pair.

Prepare standard-library MIR separately for each Cargo using `std_mir.py
--cargo-key KEY`. The screen only validates those existing artifacts; it does
not prepare them. `--std-mir-ready` must belong to A's Cargo identity and
`--candidate-std-mir-ready` to B's. A′ uses A's prepared std metadata with an
independent project cache. Every launcher completion must report the expected
Cargo executable/hash/provenance and actual std key/sysroot/target. All runtime
Cargo commands still select the same pinned public rustc explicitly.

The existing protocol is unchanged: 27 complete launcher commands, three
independent project caches, a wrong production edit, compiled recovery, five
fresh cumulative valid edits, final compiled restoration, all 14 original tests,
and equal bytecode/catalog/output/outcome checks across arms. Timing surrounds
the entire launcher/capture; setup or internal Cargo phases are not subtracted.
Paired A/B wall and waited-child CPU measurements retain the A/A′ noise control.

No real Cargo-policy screen or std setup was run while adding this policy.
It is a mechanism screen and cannot establish the final 0.5 s/generalization
claim on its own. Cargo remains excluded from fresh holdouts due to prior use.
