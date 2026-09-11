# Fresh body execution: fre / fre-kernels

Status: passed. Recollected 389 bodies in 25 batches with tool `0e94d6d82b4b734e281e5b8c95a55866e5c7b0a8be53be2dafadd410708467ee`.

| Outcome | Bodies |
| --- | ---: |
| ignored | 7 |
| passed | 382 |

The native control was built once and ran in 382 fresh test processes. Original sources, tests and strict frontend checks were preserved.

Export options: `--std-mir --inline-leaves --trap-unsupported-calls --run-try-callbacks --guest-mir-opt-level 3 --guest-mir-inline-scale 8`. Runtime options: `--jit-persistent-registers --jit-resumable-calls`.
Per-body limits: 100,000,000,000 instructions and 150,000 live allocations.

Successful runs made 959,720,554 resumable Calls and 976,188,628 Returns. Maximum generated code was 15,188,028 bytes; 0 successful executions declined functions.

Compared 382 available artifact hashes with previous coverage; 0 changed. Outcome changes: 0. Individual results and exact commands remain in `.work/resumable-copy-fre-01`.

Fresh ordinary body replay with native processes. Ignored, lowering-blocked and unsupported bodies are separate. No full libtest, unwinding, FFI or thread support claim.
This is compatibility evidence, not an edit-to-test performance measurement.
