# Final-bytecode scalar boundary admission

Use the exact integrated scalar transform as a linked module, including its
existing differential tests. For each MIR-eligible boundary slot, probe a private
copy of its final function with that single slot. The transform's returned
selection is the address-use certificate: full widths, unique definitions,
block-local dominance and no unsupported address consumers, including cold code.
Do not execute, serialize or publish the probe body: its zero-initialized
canonical register is deliberately unsuitable for a function argument/result ABI.
Entry initialization and result publication remain separate implementation work.

Bind every row to the original serialized function hash and actual final ABI
position/size. Reconcile the original profiles again with their full identity and
instruction/Call/Return totals. Classify all previously eligible rows, keep exact
access counts from the verified census, and weight direct argument copies and
returns by admitted/rejected shape. Indirect callees remain unresolved.

Bounds: original transform's 100,000 operations/registers; at most 32,768 rows and
32 million aggregate probe operations. Exhaustion is an explicit rejection, not
silent eligibility. No threshold sweep, changed guest execution or speed claim.
Nine-GiB admission leaves the existing eight-GiB floor for this small two-job
locked/offline host build. Hold the shared benchmark lock for all build/test and
analysis commands; preserve exact process and evidence receipts.
