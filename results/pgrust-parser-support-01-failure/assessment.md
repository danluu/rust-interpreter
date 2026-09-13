# Complete SQL-parser support probe: exporter failure

The pinned original pgrust `gram_core` library target passes all114 native
tests, with zero failed, ignored or filtered tests. The custom command selects
the same114 names but exits101 while lowering `Box<F, A>::call_once`:
`virtual call requires a fat-pointer receiver`. No guest test executes and no
suite report is produced. These are support checks, not performance results.

The original source and assertions remain unchanged. The terminal supervisor,
both command logs, native executable, exact test set and all4,914 frozen
source/helper/tool inputs verify in the subsequent audit. No command was
repeated. Full receipts remain under `.work/pgrust-parser-support-01`.

Investigate the general by-value dynamic receiver ABI used by boxed `FnOnce`.
The existing virtual-call path expects a16-byte stored pointer; an unsized
dereferenced place carries its data address and metadata separately. Confirm
that representation with a small native/custom regression and preserve tuple
arguments, ownership and drop behavior. Do not exclude parser tests or add a
project-specific callback substitute. A corrected exporter needs its own
qualification before a new parser support probe.
