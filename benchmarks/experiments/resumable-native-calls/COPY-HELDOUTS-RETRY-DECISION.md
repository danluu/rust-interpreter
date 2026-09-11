# Retry decision after the first separate history stopped

The first `nushell-type-relations` history stopped between commands at the
8 GiB space guard. Its [assessment](../../../results/resumable-copy-heldout-01-case-01-stop/assessment.md)
preserves five primary commands, one check, four executed snapshots, the
terminal receipts and restored source. It contains **zero successful-edit
pairs**. The wrong-edit failures are expected test failures. This is neither
a runtime regression nor a completed held-out result.

The original `COPY-HELDOUTS.json` and its frozen evaluator remain unchanged.
Before restarting, create an explicit amendment selecting
`resumable-copy-heldout-01-case-01-retry-01` for the first case, retaining the
other six IDs, case order, tools, controls, repetitions and gates. Bind the
original plan hash and stopped-history assessment. Qualify aggregation of
this exact replacement without counting the partial history or allowing
other substitutions. No timing-based retries or extra repetitions are added.

The [space regression check](../../../results/workflow-space-floor-01/assessment.md)
adds the omitted 8 GiB running floor to the historical cache estimate, 20%
growth allowance, archive reserve and evidence reserve. Admission requires
at least **27,906,753,093 bytes (25.99 GiB)** under that estimate. Obtain a new
measurement of available space immediately before launch. Do not lower the
running guard to fit a history. The estimate cannot control unrelated writes
on the shared volume.

Retiring the four reviewed stopped-history caches preserves their exact
contents in verified archives and leaves all benchmark evidence in place.
Additional space may still be needed. Existing success-only cache provenance
must not be bypassed for old reports that predate supervised/repeated runs;
any such extension needs its own bounded ownership checks and qualification.
Private caches, quarantine directories and unrelated processes remain outside
this work.

No retry has started at this checkpoint. Retention still requires all seven
complete held-out cases, the unchanged primary gates and the existing native,
TLS and fre qualifications. Neither archive work nor the disk-guard stop is
a compilation speed result.
