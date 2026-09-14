# Preparation remains a secondary runtime target

All 80 closed edited-command observations and three accounting controls pass.
The source closure verifies 109 inputs, including the adopted tool's exact counter
implementation. No guest, compiler or new timing command runs.

| Workload | Edits | Command median | Largest worker's compilation | Constructor sum |
| --- | ---: | ---: | ---: | ---: |
| token, full history | 15 | 4.048 s | 157.33 ms | 66.44 ms |
| folded | 15 | 1.574 s | 54.25 ms | 15.48 ms |
| pgrust hash | 15 | 0.504 s | 2.52 ms | 0.44 ms |
| private rg-aot | 15 | 0.228 s | 2.60 ms | 0.30 ms |
| Nushell type relations | 15 | 4.989 s | 8.19 ms | 1.97 ms |
| token, latest control | 5 | 3.969 s | 155.75 ms | 66.05 ms |

Compilation now exceeds the historical 0.7–11 ms figures cited in the old runtime
notes. Even so, the largest token worker's compilation interval is only about
3.9% of complete command time; folded is 3.4%, and the other workloads are
0.16–1.14%. These are ratios of recorded intervals, not recoverable latency.
Constructor durations overlap across workers, and code-cache loading, validation,
relocation, identity checks and writeback would introduce their own costs.

Keep persistent machine-code caching as a possible later approach. Execution
remains the larger opportunity for token; the large Nushell workload is dominated
by its compiler/Cargo workstream. Next inspect unused pure register calculations
in the ordinary native emitter, preserving all memory and fault effects. This
extends the scope of the prior private-leaf census without repeating its failed
runtime screen. A saved-code census must justify any new implementation.

[Summary](summary.json), [all aggregate observations](observations.json),
[closure](closure.json). Private identifiers and command output remain local.
