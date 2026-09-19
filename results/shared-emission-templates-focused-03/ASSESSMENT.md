# Native execution qualification for shared templates

All17focused controls pass in debug and release, source5b45cbba, original
supervisor59737/child59786. Stage1's6relocation controls and Stage2's12combined
relocation/store controls are separately closed and retained. No original
application workload was run, and all new code remains test-only.

Four native fixture tests restore templates into distinct simultaneously live
MAP_JIT arenas. The second owner is required to hit both templates. Actual
execution matches ordinary JIT values, guest instruction counts and memory
peaks across instruction prefixes0through22, five memory limits and four frame
limits. Separate controls preserve assertion/trap/memory errors and original
messages, reset static/TLS state after success and failure, and retain ordinary
emission/interpreter fallback when the store or native arena is full. A fifth
new control rejects partial-validation scope before capture/storage.

These tests publish and execute custom native fixture code. They establish a
bounded staging/publication path, not end-to-end performance or production
integration. No disk cache, compiler backend or external interpreter is used.
Next connect an explicit prepared-suite option with independent owner counters,
preserve the default path, and qualify real original assertions/strict checks
before admitting changed-source timing. Cache lookup, copying, locking and
population must remain inside those measurements.
