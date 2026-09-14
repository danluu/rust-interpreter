# Native bytecode qualification passes

The independent ten-word host-assembler oracle passes before any new native
execution. All **352 bytecode tests/profile** pass in debug and release, with
11 retained ignored diagnostics. Three commands complete 705 test passes.

New native fixtures require emitted captures and compare complete live Memory
snapshots, returned values, logical counts and per-PC profiles against the
interpreter. They cover arbitrary narrow/high-lane values, seven aligned and
unaligned destinations, overlapping copies, unknown pointer reads/writes,
assertions, and every instruction-budget prefix under both persistent settings
and profile modes. Missing/replaced producers and unexpected SIMD/call clobbers
cannot produce a reuse. All existing bytecode controls pass as well.

The first attempt failed at test compilation because the test-only Memory drop
observer disallowed three existing moves of heap snapshot buffers. Those test
assertions now clone the buffers; the failure is retained separately. Production
Memory has no new drop implementation.

Proceed to the immutable tool build, full workspace/Python checks, strict checking
and original project profiles. The native prototype is not adopted and has no
latency result. Source `c3a0738a`; [summary.json](summary.json) and
[closure.json](closure.json) bind commands, source and logs.

Receipt correction: the inherited zero-valued `guest_commands`,
`executable_code_publications` and `production_runtime_changes` fields have the
wrong scope for native qualification. [metadata-correction.json](metadata-correction.json)
supersedes them. The closed receipt and logs remain unchanged.
