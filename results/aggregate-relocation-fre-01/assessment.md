# Fresh body execution: fre / fre-kernels

Status: passed. Recollected 389 bodies in 25 batches with tool `9637b0acb1d208524c3c8b446af64cfd5e2d0d3be75e1412a8df76750ce36223`.

| Outcome | Bodies |
| --- | ---: |
| ignored | 7 |
| passed | 382 |

The native control was built once and ran in 382 fresh test processes. Original sources, tests and strict frontend checks were preserved.

Export options: `--std-mir --inline-leaves --trap-unsupported-calls --run-try-callbacks --guest-mir-opt-level 3 --guest-mir-inline-scale 8`. Runtime options: `--jit-persistent-registers --jit-resumable-calls`.
Per-body limits: 100,000,000,000 instructions and 150,000 live allocations.

Successful runs made 990,784,739 resumable Calls and 1,007,252,714 Returns. Maximum generated code was 15,077,816 bytes; 0 successful executions declined functions.

Compared 382 available artifact hashes with previous coverage; 382 changed. Outcome changes: 0. Individual results and exact commands remain in `.work/aggregate-relocation-fre-01`.

Fresh ordinary body replay with native processes. Ignored, lowering-blocked and unsupported bodies are separate. No full libtest, unwinding, FFI or thread support claim.
This is compatibility evidence, not an edit-to-test performance measurement.
