# Fresh body execution: fre / fre-kernels

Status: passed. Recollected 389 bodies in 25 batches with tool `78e60cdd76195c55583651bac6a7f7d349314dd1ea582b6a86335adbee48049d`.

| Outcome | Bodies |
| --- | ---: |
| ignored | 7 |
| passed | 382 |

The native control was built once and ran in 382 fresh test processes. Original sources, tests and strict frontend checks were preserved.

Export options: `--std-mir --inline-leaves --trap-unsupported-calls --run-try-callbacks --guest-mir-opt-level 3 --guest-mir-inline-scale 8`. Runtime options: `--jit-persistent-registers --jit-resumable-calls`.
Per-body limits: 100,000,000,000 instructions and 150,000 live allocations.

Successful runs made 959,714,888 resumable Calls and 976,181,341 Returns. Maximum generated code was 15,173,088 bytes; 0 successful executions declined functions.

Compared 382 available artifact hashes with previous coverage; 0 changed. Outcome changes: 0. Individual results and exact commands remain in `.work/resumable-bulk-fre-01`.

Fresh ordinary body replay with native processes. Ignored, lowering-blocked and unsupported bodies are separate. No full libtest, unwinding, FFI or thread support claim.
This is compatibility evidence, not an edit-to-test performance measurement.
