# Avoid costly whole-function emission for the oversized tier

The closed diagnostic identifies repeated failed native emission of a140,615-op
function:21–23ms ordinary staging plus4.6–5.3ms scalar-callee preparation per
worker, about14.4MB staged then discarded at the remaining arena budget. This
is direct actual-suite evidence; durations overlap and are not predicted savings.
The prior larger-arena and conditional-demand experiments remain failed.

The explicit jit-large-function-interpreter feature uses the existing65,536-op
analysis boundary as a compilation-cost heuristic. A larger resumable function
stays interpreted before scalar-callee or ordinary staging; smaller callees still
prepare independently when reached. This does not prove every large function
would fail emission. It may regress large compilable hot functions, so adoption
requires all original project guards. No source-specific names, IDs or sizes.
Default builds retain their policy. Server readiness records the threshold, and
its executable hash binds the complete policy. Diagnostic observation is off.

Compose with qualified request-cost sessions; exact artifacts still receive full
Rust type/borrow checking, structural validation and current runtime admission.
Fresh native/guest/environment state, bounded memory/history/code and no replay
remain. Qualify442Python+22skip,652Rust/profile+16ignored and a feature-off VM.
The new boundary control compares actual execution, budget failures and fresh
runs against the interpreter and checks smaller callees still compile. Include
all current stale-input/reservation/transport controls. Replay16 saved actual
parser suites with every restored template independently verified before timing.

Use the unchanged five-mode40-command primary, including two strict rejection
controls, full kernel CPU/lifecycle allocation and original A/A/CPU gates. Only
this material candidate may enter; do not retime the prior failed one. A primary
failure parks larger comparisons; a pass requires the five-project regression
campaign before adoption. Compiler/exporter/wrapper remain unchanged.

Hold .work/benchmark.lock,45s admission,two workers; shared target
.work/fixed-frame-clear-combined-build-01/target never cleaned. Build floor
max(14GiB,8GiB+2*allocated target), replay12GiB, child/closure8GiB. Primary initial
24GiB and16GiB cache allowance stay fixed. Preserve every failure, source/evidence,
private data and peer process/worktree. No subagents, goal calls or new services.
