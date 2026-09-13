The composed current compiler and exact measured runtime pass all 119
strict/cache/Cargo controls. Native, custom interpreter and custom JIT results
agree on the original environment, dynamic-dispatch and closure-pointer
fixtures. Cold/warm reuse preserves bytecode; helper edits change the intended
result and restoration recovers the original bytes and output.

Uncalled type/borrow errors stop the Cargo launcher before guest execution.
Automatic cache mode also behaves correctly with incremental compilation
turned off. Invalid C-string reads and incompatible external signatures retain
their required failures. These are compatibility controls, not timing evidence.
The real-project histories and complete parser remain pending.
