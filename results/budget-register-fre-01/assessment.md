# Fresh body execution: fre / fre-kernels

Status: passed. Recollected 389 bodies in 25 batches with tool `366567663f043d4a2370d72ae7eeade60bb91cda07ac19e12831491b4f606504`.

| Outcome | Bodies |
| --- | ---: |
| ignored | 7 |
| passed | 382 |

The native control was built once and ran in 382 fresh test processes. Original sources, tests and strict frontend checks were preserved.

Export options: `--std-mir --inline-leaves --trap-unsupported-calls --run-try-callbacks --guest-mir-opt-level 3 --guest-mir-inline-scale 8`. Runtime options: `--jit-persistent-registers --jit-resumable-calls`.
Per-body limits: 100,000,000,000 instructions and 150,000 live allocations.

Successful runs made 990,782,256 resumable Calls and 1,007,250,388 Returns. Maximum generated code was 15,271,588 bytes; 0 successful executions declined functions.

Compared 382 available artifact hashes with previous coverage; 0 changed. Outcome changes: 0. Individual results and exact commands remain in `.work/budget-register-fre-01`.

Fresh ordinary body replay with native processes. Ignored, lowering-blocked and unsupported bodies are separate. No full libtest, unwinding, FFI or thread support claim.
This is compatibility evidence, not an edit-to-test performance measurement.
