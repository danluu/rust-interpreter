# Reader audit 04: failed

The Reader03 run passed. The second independent verifier attempt rejected the original hash-driver receipt because it expected its qualification flag to be true. That immutable receipt correctly says it awaits independent verification; the separate completed audit supplies the qualification.

The verifier child exited with status 1 and produced no verification report. Its complete source, raw output and process record are preserved here. No compiler ran and no files were retired. A corrected auditor must preserve the distinction between the original receipt and its later audit. This failure is not a performance measurement.
