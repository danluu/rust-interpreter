# Why the large parser function remains interpreted

The actual resumable, persistent-register emitter can encode the complete
`reduce_cold` function, but its native code nearly fills the entire code arena.

| Offline staging mode | 16 MiB word allowance | 64 MiB word allowance |
| --- | --- | --- |
| Ordinary counters | Emits 16,554,488 bytes | Same 16,554,488 bytes |
| Logical profiling | Declines for code budget | Emits 17,666,044 bytes |

Both successful forms cover 140,554 operations and 29,568 entries. No encoding
error occurs. The function has 140,615 total operations, 102,786 registers and a
372,497-byte frame; its fresh resumable table fits. An unprofiled full function
leaves only 222,728 bytes in the supported 16 MiB code budget. The observed
prepared workers already publish about 2.7 MiB while reaching their first tests,
and the fresh profiled run cannot fit this function even in an otherwise empty
arena. A budget increase, rather than a branch-encoding repair, is the relevant
simple comparison.

The larger allowance applies only to staging vectors inside one explicitly
ignored diagnostic test. Four offline emissions publish no executable code and
execute no guest instruction. Production limits and runtime code are unchanged.
The one diagnostic test passes; source/artifact hashes and its command receipt
are retained. Static code size does not establish a speedup. Next compare a
bounded capacity alternative and evaluate how much of the function is actually
reached before investing in lazy region compilation.
