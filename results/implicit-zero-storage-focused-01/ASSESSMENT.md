# First focused attempt

Six controls pass; the persistent-reload fixture fails before native execution.
Its single read does not meet the allocator's two-read eligibility rule, so the
real allocator correctly produces no assigned pair. Add a second read to obtain
the intended assignment. No production defect was identified by this failure.
The release command was not started. Preserve source979dd263, all command logs
and supervisor84616/child84658. The next attempt also adds TLS callback and
indirect-handle boundaries, with fresh source and a new run namespace.
