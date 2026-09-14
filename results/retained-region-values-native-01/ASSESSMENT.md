Native qualification stopped at test compilation before the encoding oracle or any JIT execution. The new test-only Memory drop observer prevents moving `m.heap.bytes` out of Memory in three existing test assertions (two compare-bytes and one CPU-query check). Clone those test snapshot buffers and repeat under a new run ID. No native instruction or project workload ran; the prototype remains unqualified. Source `05624681`.

Receipt correction: the inherited zero-valued `guest_commands`,
`executable_code_publications` and `production_runtime_changes` fields have the
wrong scope for native qualification. [metadata-correction.json](metadata-correction.json)
supersedes them. The closed receipt and logs remain unchanged.
