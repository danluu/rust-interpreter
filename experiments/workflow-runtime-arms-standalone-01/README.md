# Standalone per-arm runtime runner proposal

This fresh proposal preserves the committed per-arm source proposal, its passed35 controls, and all R scripts. Intended deployment is the new R/experiments/workflow-runtime-arms-01 directory; it has not been created.

Copy the four non-test proposed files into that fresh directory only after parent approval. The two entrypoints use the adjacent placement helper to select the adjacent runner/runtime-arm helper before the original R/scripts modules. Both interpreter source and provider ROOT are checked. The saved verifier obtains ROOT from that selected runner. Provider installations and child interpreter/native-suite paths stay R-owned. The runner freezes the helper's actual module path and the new placement helper.

All runner function ASTs are unchanged from the qualified proposal after normalizing only that source-freeze list. Every verifier function is identical. The pure runtime-arm helper is byte-identical to the passed35 version; those tests were not repeated.

Thirteen new placement tests passed once under isolated Python -I -B discovery using owned temporary script stubs. They cover both entry routes, search precedence, wrong/stale modules, wrong ROOT, missing helper and symlinked routes. Exact command/source hashes, raw output and waited-for process closure are retained in results/workflow-runtime-arms-placement-controls-01. No real provider or benchmark module was imported by those fixtures.

help-source-inspection.json gives the exact two future --help commands and the complete source-only import graph. Both help paths exit before provider lookup, locking, report/source reads or child execution. They import API definitions and inspect script placement only. No actual help smoke run has occurred because deployment remains absent while runtime04 preparation is active.

No R script, provider, application source, fixture or holdout was changed. There is no new audit/controller framework or provider-root override.
