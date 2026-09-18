# Ruff HIR cache diagnostic

The existing six Ruff tests passed for both cache settings across the original source, five production edits, and restoration. The intentional wrong edit failed in native, cache-off, and cache-on modes. All 11,119 source files were restored; all eight paired off/on bytecode snapshots match. The original and restored snapshots differ in both modes, so this is not a claim of bytewise restoration of compiler output.

The cache-on configuration regressed this instrumented history:

| Median of five edits | Cache off | Capture and reuse on |
|---|---:|---:|
| Build to validated artifact | 3.228 s | 4.124 s |
| Complete test command | 3.348 s | 4.253 s |
| Exporter compiler frontend | 2.318 s | 3.121 s |
| Exporter MIR-to-bytecode and publication | 0.122 s | 0.125 s |

The native complete-command median was 6.165 s. These are diagnostic observations from one edited history with incremental-info and Cargo timing enabled, not an uninstrumented performance qualification. The execution route explicitly permits unavailable-call traps and try callbacks; the strict 0.5-second goal remains unmet.

Each warm custom call launched only the `ruff_linter` test compiler. A subsequent review corrected the initial interpretation of its aggregate stderr: Cargo replayed 1,510 old capture messages from 18 fresh dependency fingerprint files before the selected compiler started. The actual selected compiler emitted 1,411 verified hits and zero captures in each of the seven warm states. These counts do not include gated or unreported bodies and therefore provide no whole-crate coverage denominator. The archive preserves the original audit, the explicit correction, the exact cached diagnostic files, and the source of both reviews.

`frontend` is the interval from exporter callback construction to its `emit` entry. `lowering` includes MIR-to-bytecode conversion, validation, serialization, hashing, and artifact publication; it does not mean rustc AST-to-HIR lowering. No compiler self-profile was enabled, so these aggregates cannot identify which internal cache checks or compiler phases caused the regression.

The archive retains all 24 command records and raw output, eight native identity probes, 16 bytecode snapshots, 24 Cargo timing reports, all 154 frozen input copies, and the complete HIR event record. The ordinary workflow retains a PID and argv per call but only its final active-command process receipt; complete contemporaneous parent/time receipts for every application call are not claimed. Archive proposal 01 remains unrun and is retained with the corrected, successful proposal 02. No application command was rerun during analysis or retention.
