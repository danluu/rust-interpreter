The narrowed built-phase observer passes all 133 command checks and preserves all eight bytecode artifacts exactly relative to the uninstrumented reduction. It reproduces allocation counts 1/1/2/2 with incremental reuse and 1/1/1/1 without it.

| State | Built-MIR dumps written, incremental on | Incremental off |
| --- | --- | --- |
| Original | first, depends_on_api, third | all three |
| Wrong API body | none | all three |
| Generic API signature | depends_on_api | all three |
| Restored signature | depends_on_api | all three |

Per-state before/after file identities, modification times and SHA-256 values are retained in the raw dump-change records. The fixed dump directories preserve their final files. On the pinned compiler, mir_built calls build_mir_inner_impl and then dump_mir_for_phase_change; the built-phase dump is emitted when that body-building query runs. Thus this reduction directly observes selective MIR rebuilding where the allocation split appears, while first and third retain cached bodies.

Together with the compiler allocation-decoder and literal-construction source, this supports the mixed cached/recomputed MIR explanation. IDs remain session-local and cannot serve as cross-build cache keys. No equal-content allocation merge or performance improvement is claimed. The earlier broad-pass attempt correctly refused additional NLL .dot/.html outputs; its failure and source restoration are preserved. The observer was narrowed to built-phase .mir files.
