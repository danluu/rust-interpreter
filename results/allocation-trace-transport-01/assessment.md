# Allocation sidecar transport qualification

The new optional transport helper accepts all four original exporter traces
and checks their exact artifact hashes, event counts and trace sizes. It passes
33 rejection checks: truncation, wrong artifacts, schema/order/parent errors,
repeated boundaries and JSON fields, nonfinite values, invalid UTF-8, missing
or replaced files, symlinks, FIFOs, directories and size/event overflow.
Exact byte and event limits pass. Supervisor 36859/controller 36862 finished
successfully. Original fixture/artifact hashes remain unchanged.

Reading is bounded to 64 MiB, regular files are checked before and after opening,
and a final hash-bound completion record is required. The offline inspector
still provides the deeper allocation/relocation checks. This helper checks
transport and binding; it does not prove equivalence across compiler sessions.

The production launcher remains frozen for the worker study. No launcher flag,
large-project trace, guest behavior change or performance improvement follows
from this qualification alone. See [results](summary.json).
