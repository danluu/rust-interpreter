# Proposed metadata inspection before assembly

This is an unexecuted inspection proposal. The reviewed compositor and its eight
synthetic controls are separate. No actual build stamp, compiler artifact, beta
archive, or current compiler source inventory has been read by this proposal.
Saved source/build/qualification metadata was read to prepare it. The proposed
next operation writes only a fresh evidence directory; it does not assemble B,
compile anything, delete outputs, or change any bootstrap flags.

Use the existing external supervisor and owned_stage canonical lock with a
600-second bound. Keep the ordinary 8 GiB running floor while retaining small
proof payloads. Freeze the exact inspector source/imports and the reviewed
`INSPECTION.json` before launch. Record actual Python identity, argv, PID,
parent, cwd, environment, lock admission and terminal receipt. A timeout or
failed guard is retained; there is no automatic retry.

The input graph is explicit in `INSPECTION.json` and `INPUTS.json`:

1. Validate the archived native qualification (`373719cd…`, 1,012 members,
   335 actual hits) and saved successful native005 `./x build --stage 1
   compiler/rustc library --jobs 2 -vv`, including exact argv, environment,
   child/supervisor identities, return code and both raw output hashes.
   Preserve the original outer parser failure and later completed replay as
   distinct facts. Keep the retained seven earlier source/build histories.
2. Reuse the already frozen HIR stage2 helper's `qualified.previous`/archive
   validation and `engine.source_guard` on the actual 7efc source record. The
   source guard checks all 62,708 recorded source files plus 102 backtrace files,
   the exact owned-source marker/configuration and five recorded Git guards.
   Freeze its complete 135-input helper map from the reviewed materialized
   stage2 plan; importing the helper does not authorize its stage2 actions.
   Recheck the complete 64-file qualified E runtime and the two exact source
   links through the existing native artifact helper. Retain proof metadata,
   not duplicate compiler binaries or the entire source checkout.
3. Read the exact current `.librustc-stamp` once through an ordinary-file guarded
   descriptor. Retain raw bytes, SHA, size, dev/inode/nlink, mode, mtime/ctime,
   all h/t/s rows and basename destinations **before** membership validation.
   Compare its identity/timestamps with the successful build and subsequent
   recorded bootstrap history; a timestamp is supporting evidence, not a
   substitute for source/producer consistency. Unknown tags, paths, link types,
   duplicate destinations and unexplained later production remain explicit.
   Do not recursively traverse stage1-rustc, derive membership by glob, or
   replace the complete stamp with the 219 saved extern references.
4. For each exact stamped path, read/hash that ordinary file, retaining
   size/mode/dev/inode/nlink/mtime/ctime and before/after equality. Record every
   applicable evidence edge listed below. Full-path matches precede any crate
   names; names merely help present already bound records. Keep ordered,
   repeated --extern bindings and their original command/line hashes.
5. Hash both pinned beta archives and inventory every member. Use the
   compositor's ordinary-member selection for their complete lib subtrees;
   compute selected member hashes, sizes and destination names without
   extracting them. Hash the exact original downloaded D compiler executable
   and reconcile its corresponding archive member. Record D's genuine archive
   provenance separately from E. No `-vV`/sysroot or compatibility compiler
   subprocess belongs to this metadata-only phase.
6. Recheck all source/runtime/stamp/artifact/archive identities at the end.
   Preserve every row, including rows needing further review, and publish the
   complete candidate path -> `{sha256,size}` map with a separate evidence
   classification. The map is not yet an approved assembly input. Only after
   root reviews the actual set and any unresolved relationships should the
   admitted runner pass an approved full map to `inspect_inputs` and freeze its
   exact composition plan. No row may disappear between these two maps.

Per-row evidence distinguishes how Cargo satisfied the completed build:

| Classification | Required retained evidence | Meaning |
| --- | --- | --- |
| Direct rustc producer | Exact saved Running argv, out-dir, crate type, extra-filename and emit arguments deriving this full output path; normal flags and successful outer command | This compilation ran in the recorded history |
| Exact consumed dependency | Every complete matching `--extern` path and consumer argv/line hash, including paired rmeta/rlib bindings | The normal compiler consumed this dependency; it need not have been rebuilt in005 |
| Native build-script output | Exact recorded build-script OUT_DIR/path, its normal Cargo command and relevant link-search/link-lib output, with complete stamp membership | An ordinary native prerequisite, with separately recorded source/recipe association |
| Stamp-mediated reused input | Exact completed-build stamp membership, unchanged current source/runtime, saved successful native build history and any Cargo Fresh/consumer records | Legitimate reuse can be consistent without a repeated producer argv; do not invent a missing command |
| Unresolved or conflicting | Complete raw row/hash and the precise missing or contradictory association | Root must review it before any assembly; it is never silently omitted |

The saved native005 stdout/stderr has 215 Running lines and 183 Fresh lines,
but no retained `compiler-artifact` JSON: bootstrap consumed those messages.
Thus "not recompiled in005" is not itself a rejection. The full successful
stamp and unchanged source/runtime provide the common provenance boundary;
the eventual D compiler still performs ordinary private-metadata/SVH checks,
and the smoke proves actual E driver loading. No handcrafted metadata
compatibility label can replace those checks.

The compositor currently confines stamp files to the two exact
stage1-rustc release roots. If actual rows contain stage1-std or another
legitimate dependency root, retain and classify those rows without applying
`parse_stamp` as a reason to discard them. A reviewed explicit extension is
required before assembling them. Capacity cleanup and its failed inventories
remain paused and are not part of this inspection.
