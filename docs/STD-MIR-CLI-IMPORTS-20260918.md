Standalone `scripts/std_mir.py` now loads the custom compiler and Cargo helpers only when their respective selection keys are present. Selected-tool loading order, forwarding and errors remain unchanged; 21 focused tests passed.

A fixed 20-pair experiment measured 3.88% less CPU in actual stock import/main and prepared-cache reuse, with 18 paired wins. Whole-driver CPU fell 1.89%. Compiler discovery was stubbed and a process-denying audit hook remained inside the measured region, so these results describe that instrumented CLI route. They do not establish a full build, interpreter-launcher or holdout improvement.

[The retained evidence](../results/buildtime-std-cli-imports-20260918/evidence/README.md) includes every sample, source/runtime binding, frozen decision, qualification result and audit. All eight acceptance gates passed without retiming or sample exclusions.
