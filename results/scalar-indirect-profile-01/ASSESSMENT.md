# Original profiles preserve semantics and expose the intended mechanism

All three original tests pass exact logical-PC counts, instruction/peak-memory
counts, entropy identity and complete same-process native-code reconstruction.
Scalar Calls remain11,227,102 /16,298,574 /1,585,153. Native indirect transitions
execute1,025,927 /843,753 /30 calls, leaving20 /23 /3 cold or declining calls
interpreted. JIT entries fall by exactly those native counts. Code grows by
29,216 /27,000 /4,412 bytes, all below the unchanged16 MiB cap.

Three candidate commands reuse three closed adopted controls. Diagnostic entropy
replay establishes identity only and will not be used in timing. Closure verifies
74 frozen inputs and24 artifacts. Next: original40-command full-token real-edit
primary; all12 original tests and unchanged A/A wall/CPU gates. No speed claim.
