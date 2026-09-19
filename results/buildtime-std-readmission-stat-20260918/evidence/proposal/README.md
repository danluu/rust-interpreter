# Reuse one stat observation during ordinary std-MIR validation

This is an unexecuted, isolated source proposal against /Users/danluu/dev/rust-interp-allocation-decoder-publication-20260918 at f38004cbd3392b5a6763f920d80801826bbde77c. Nothing has been applied to a worktree or imported, tested or measured. candidate.patch changes only scripts/std_mir_readmission.py and its existing test module. The source/ and baseline/ directories retain exact candidate and baseline copies, with hashes in source-bindings.json.

The repeated setup route is interpreter._main (--std-mir) -> std_mir.checked_std_mir -> the ready-manifest branch of _checked_std_mir_locked -> std_mir_readmission.validate. That validator always iterates metadata artifacts before deciding whether stamps already match or a saved readmission receipt can be reused. The current loop calls Path.is_file followed by Path.stat. Local pinned Python3.14 pathlib/genericpath source shows that both perform os.stat, while is_file uses only the first result's regular-file mode.

The proposed successful path performs one Path.stat and uses its result for both stat.S_ISREG and the existing device/inode/size/mtime stamp. It follows the same symlink target. It does not cache an observation across calls, omit an artifact, reduce the stamp fields, or stop checking after an early stamp mismatch. The retained owned 26-artifact ready manifest illustrates 52 ->26 initial stat calls by source count; this is not a timing result.

Errors use a conservative slow path. If the initial stat raises OSError or ValueError, the candidate first leaves that exception handler and then runs the original is_file/stat sequence unchanged. Thus each runtime's public Path.is_file still decides which errnos to suppress or propagate, including older Python versions that propagate permission or I/O errors. The unchanged RuntimeError remains outside the active stat exception handler, preserving its empty cause/context for ordinary missing/nonregular cases. This fallback avoids copying private pathlib errno tables. Stable error cases can perform one additional failing stat; no claim is made that those cases get faster.

After the initial loop, all production text is byte-identical, including:
- complete current/original comparison and uniform-device-only eligibility;
- ready-manifest SHA and exact cached-receipt comparison;
- regular-file fstat and initial stamp checks before actual hashing;
- complete content digest and post-hash fstat;
- final path-stamp and ready-manifest-hash verification;
- exclusive temporary receipt creation and atomic publication.

The artifact order and the fact that all initial file-type checks precede the aggregate stamp comparison remain unchanged. Successful type and stamp now come from one stat result. Concurrent mutation precisely between the old two syscalls necessarily has a changed observation boundary; this proposal does not claim identical outcomes for every adversarially timed mutation. It retains the caller's std-mir lock, immutable-metadata assumptions and every independent readmission check. General mutation detection beyond the existing stamp/content contract is not added or claimed.

## Qualification coverage

All seven existing tests and their helpers are AST-identical. Four new tests are proposed, making eleven per arm and 22 paired test executions:
- Actual missing files, directories, dangling symlinks and symlinks to directories retain the exact artifact error and leave ready/receipt state unchanged.
- An actual symlink to a regular artifact remains accepted during complete readmission, saved-receipt reuse and already-matching-device reuse; payload, manifest and receipt remain unchanged where required.
- Stable ENOENT, ENOTDIR, EACCES, EPERM, EIO, ELOOP, ENAMETOOLONG and ValueError outcomes use the runtime's public Path.is_file as their suppression/propagation oracle. Only the named artifact's os.stat is faulted; type, arguments, cause/context, manifest and receipt state are compared. No stat-call count or fast-path branch is asserted.
- A later missing artifact keeps precedence over an earlier artifact's stamp mismatch.

The existing tests retain changed-content/restored-stamp rejection, mixed and nondevice stamp changes, replacement/missing artifacts after readmission, mutation while hashing, changed receipt and full hashing/reuse coverage. A future qualification should execute the same eleven-test candidate test module against each arm's actual production module with canonical imports; do not substitute candidate production while claiming a baseline run. Pinned Python3.14 is the existing controlled runtime. If an older supported interpreter is available, the stable-errno test intentionally derives its expected behavior from that interpreter rather than assuming 3.14's policy.

## Prospective measurement and risks

No decision thresholds or schedule are frozen by this source proposal. Before any timing, the parent should freeze an actual-public-validate comparison with two reused metadata states: exact saved stamps and an already validated uniform-device readmission receipt. Use one shared owned fixture per state, prepared through actual baseline validation, then immutable during measurement. The exact current retained artifact count is preferable to an exaggerated filesystem corpus. Small artifact content is sufficient for these two reuse paths because neither reads contents; complete hash-readmission remains part of semantic qualification.

Measure the actual validation call and independent full child CPU/wall/RSS with fixed alternating pairs, one admitted private cache regime, artifact/outcome parity, no retiming and fixed regression guards. Any full std-setup claim would require a separate inclusive route including compiler identity and ready-manifest handling; component timing alone cannot establish a whole-build or unknown-holdout win. This may save too little absolute time to qualify once full process/setup costs are included.

production-ast-diff.json records the exact before/after initial-loop AST. Replacing that one loop in the candidate AST with the baseline loop makes the full module AST equal. The rest of the production file is also byte-identical. Those are source review proofs, not test or performance results. The proposal does not overlap parked C4/C5/C7 or C8's tempfile import placement.
