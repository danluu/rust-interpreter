# C9 fixture qualification

This packet prepares two small, owned synthetic fixture trees for the frozen std readmission timing protocol. It records correctness and provenance, not performance.

The fixed decision is decision-plan.json (SHA256 a10f461883b1b3d68416b23c863d304a3c7f3b65edba2fc35fe8f5beb630c76b). Preparation requires the successful primary 24-test receipt 26d9bb17cd6abf6839c22a7e795af39c868e0c8657ae032b98f0c3206dc29a9a and the independent Python 3.9 compatibility 24-test receipt 3157f8de282d7af4d43cc218557341273d9a331b7a007158fef341628923a843. The candidate's optimization guard was true on pinned CPython 3.14 and false on CPython 3.9. Both arms used the same 12 semantic tests per stage.

run-fixture-qualification.py --prepare-frozen-fixtures requires the pinned Homebrew Python 3.14 with -I -S -B. It takes the shared benchmark lock and creates only the fresh fixture-qualification-01 output. Exactly one memory admission child and one baseline preparation child are permitted. The eight resource/receipt helper ASTs are unchanged from the reviewed C7 semantic controller. Every child has a fresh 16 GiB disk admission; the preparation child also requires a fresh memory reading of at least 30%. A read-only observer records disk status at five-second intervals, and wait4 settlement is retained even if an intermediate record write fails. No process is signaled.

The preparation child uses -I -S -B -X pycache_prefix=.../qualification-pycache. This prefix must stay empty and belongs only to qualification. The timing screen creates a separate fresh common cache prefix; qualification cannot warm that cache.

## Fixtures and actual API calls

The sole production module imported by the preparation child is the bound baseline scripts/std_mir_readmission.py from the clean publication tree at f38004cbd3392b5a6763f920d80801826bbde77c. Its actual public validate(work, ready, result) is called exactly three times:

1. matching_saved_stamps: 26 artifacts have the current recorded stamps; validation returns None without creating a receipt.
2. matching_device_readmission_receipt: the recorded device number is uniformly current device plus one, while inode, size and modification time match. Actual baseline validation hashes all 26 artifacts and creates its own receipt.
3. The same second fixture is validated again; it returns None through receipt reuse, preserving the receipt and ready bytes and identities.

Artifacts use the exact 26 relative path names from the retained ready manifest, with 1 KiB synthetic payloads. Each payload is SHA256 of the bytes std-readmission-stat-v1, a NUL, and the UTF-8 relative name, repeated 32 times. These files are not Rust metadata. Only the retained 8,457-byte ready JSON is read; its original 112,958,025-byte payloads are neither read nor copied. Each fixture contains 26,624 synthetic artifact bytes.

Payload files and ready JSON are made read-only before admission; the real receipt is sealed after reuse, followed by directories. The complete fixture tree is bounded at 256 entries, 64 KiB per regular file and 1 MiB total. Snapshot reads use O_NOFOLLOW | O_NONBLOCK, opened-descriptor identity checks, at most recorded length plus one byte, and post-read descriptor/path identity checks. An audit hook rejects child processes, network activity, and mutations outside the owned output.

## Descriptor consumed by timing

fixture-qualification-01/fixtures.json contains status, the decision and shape hashes, the exact baseline source proof, imported source/dependency proofs, root, a complete root_inventory, and cases as a list in frozen case order. Each case contains:

- name, absolute work and ready, the complete actual parsed result dictionary, ready_proof, and exact ready_text.
- receipt: null for matching stamps; otherwise the actual absolute path, complete proof, exact text and parsed dictionary.
- inventory, artifact_count (26), and synthetic_payload_bytes (26,624).

Each inventory has entries keyed by the relative path (including the root), total_file_bytes, and entry_count. Every entry records kind and the full stamp [device, inode, mode, size, mtime_ns, ctime_ns, nlink]. Regular files additionally record byte count and SHA256. The driver records all three calls' outcomes, errors, stdout and stderr separately and in the descriptor. Successful outcomes are exactly None with no output. Its loaded input inventory must remain identical across preparation.

The timing driver consumes the full parsed result without recreating the production algorithm. It verifies the entire qualified fixture inventory before and after its single actual API call outside component clocks. The matching device route uses the already-created receipt. No fixture creation or content-hashing recovery is part of either timed case.

The preparation controller's terminal result.json includes exact prerequisites, before/after source bindings, both child settlements, three actual call outcomes, and the descriptor path/proof. Failure artifacts are retained and no retry is automatic.

## Source-only provenance

pre-unit-receipt-binding/ preserves the unbound controller, descriptor, preparer and source proof. Finalization only bound the two successful correctness receipts and corrected the descriptor's descriptive shape_sha256 field to the actual frozen shape-file hash. The preparation driver's bytes and all resource helper ASTs remain unchanged. fixture-source-proof.json records the exact derivative and current source hash checks. No fixture or workload was executed while authoring this packet.
