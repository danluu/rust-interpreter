# Full parser compiles; environment reads are the next runtime gap

The coordinated32,768-function candidate passes89 exporter tests per profile,
including cache round-trip at10,001/32,768 entries and independent reader/writer
rejection at32,769. The full original parser selection now lowers11,832 functions
and1,179,805 operations into29,445,247 bytes of bytecode. No function scheduling,
test selection, source assertion, profile setting or byte-size bound changed.

All114 custom test bodies execute in the prepared two-worker suite:7 pass and
107 fail at the same unsupported foreign `getenv` call. The exact names, all
outcomes, effective runtime limits, full4,918 frozen inputs, bytecode/catalog
hashes and reused native114-test proof validate in the guest audit. No command
was repeated. These are support results, not end-to-end speedup measurements.

Implement a general, checked environment-read primitive next. Return actual
child-process environment values from an immutable snapshot, preserving raw
Unix bytes, absent versus empty values, stable guest addresses and fresh guest
storage. Do not hard-code missing values, suppress parser errors, exclude tests,
or treat environment reads as permission to emulate missing unwind behavior.
Capacity and diagnostics remain experimental until this broader workflow is
qualified; main currently contains only the separately qualified FnOnce fix.
