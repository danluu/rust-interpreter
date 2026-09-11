# Completed-debug cache selector qualification

The new selector passes 26 rejection checks and six actual CLI rejection checks.
Three completed host workspace checks reverify their original sources, logs and
test totals after object reclamation. All four cache modes from the completed
worker cold01 history still derive their original targets. An owned host-cache
fixture passes prepare, decoded archival, retirement, inspection and restoration;
changed external evidence and repeat applications are refused. No real compiler
cache was retired by this qualification.

The selector requires the default debug workspace test profile and no installed
tool publication. Its canonical target is derived from the completed check, and
all qualification evidence must be outside that target. The existing benchmark
lock serializes host builds and retirement.

Two qualification-driver failures are preserved separately: run01 had an
unmatched parenthesis and ran no checks; run02 used the earlier fixture snapshot
for archive inspection, overlooking changed access times in the prepared
manifest. Both drivers and failure receipts remain; the corrected run03 passes.
Supervisor 74355 and its recorded child finished successfully. See
[results](summary.json), [first failure](../host-cache-selector-01/summary.json)
and [second failure](../host-cache-selector-02/summary.json).
