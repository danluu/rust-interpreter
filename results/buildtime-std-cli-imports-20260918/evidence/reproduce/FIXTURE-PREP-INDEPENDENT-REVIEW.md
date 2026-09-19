# Independent fixture-preparation source review

PASS for unexecuted fixture-prep.py9729513d49a08a0165e65d58f743ee8109d7656f4fbc8dd89036e9d98707a90e (11,058 bytes). No correctness, ownership or retention blocker found. INPUTS_SHA remains UNBOUND and must be frozen with the separately reviewed controller before execution.

Source check8381bf independently confirmed seven literal helper copies from published C9: require, disk, stamp, file_proof, save, inventory and audit. The bounded reader uses no-follow/nonblocking open, full opening/post identities and recorded-size-plus-one bounds. The inventory rejects symlinks/special entries and limits entries/individual bytes/total bytes to256/64KiB/1MiB. Output saving is exclusive and restricted to canonical paths below the owned output.

Both actual source hashes match the bound baseline/candidate versions; AST parsing reads only FLAGS/POLICY constants, without importing project code. Both corpus files are the same1,494 bytes with the pinned hash/toolchain. The exact historical shape hash supplies26 distinct safe six-component rmeta paths. No historical metadata payload is read or copied.

The freshly absent fixtures root is created only below the canonical parent-controller output. All intended artifacts are deterministic1,024-byte synthetic files (26,624 bytes total), with hashes and actual saved stamps captured after read-only chmod. The source Cargo.lock and corpus are read-only. The precreated empty std-mir.lock remains0600 because actual checked_std_mir opens it in append mode; its bytes/stamps are nevertheless part of the frozen inventory. Directories remain owned and inventoried; this is change detection, not a claim that directory mode forbids all mutation.

Compiler text includes the exact host line consumed by the real stock route. The identity fields and json.dumps(sort_keys=True) key algorithm match _checked_std_mir_locked. Ready owner, identity, metadata sum and the six expected report fields agree with actual main. The synthetic source hash is labeled accordingly; no synthetic bytes are presented as valid Rust metadata. Preparation itself performs zero project imports/calls. Actual main/readmission qualification remains the fixed parity pair.

The descriptor matches timing-driver06ad506b: schema_version,fixture_owner,compiler_sysroot,fixture_output_root,toolchain,artifact_count,compiler_text,expected_report. The controller adds arm,source_root,warmup,pycache_prefix and must bind the full fixture inventory before/after API calls. Descriptor output is a sibling of fixtures, so saving it does not mutate the captured fixture root inventory.

The post-admission audit hook prohibits process/network launch and writes outside owned output. Source creation is bounded and failed/partial attempts are retained, never reset or cleaned. No fixture-preparation child or actual API call occurred in this review. Only this note was written after fresh direct disk admission above16GiB.
