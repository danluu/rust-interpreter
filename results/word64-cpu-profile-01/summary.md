# Remaining word64 execution costs

Separate diagnostic runs sampled only the VM child processes started by this
task, recording PID/parent/start time/command/cwd and their memory maps. Sampling
was outside all benchmark runs. These short windows guide investigation; they
are not whole-run timings or confidence intervals.

In the MIR-level-3 window, about 24% of 1,553 sampled leaf PCs were in the
anonymous executable mapping containing our JIT code. Named leaf functions
included the VM loop (30%), register-vector resize (12%), checked memory copy
and platform memmove (14%), JIT entry/return handling (5%), switch-case search
(3%), and platform memset (3%). The large VM-loop symbol includes dispatch and
inlined call/frame management, so its samples cannot all be assigned to branches.
The default-MIR profile similarly emphasizes the VM loop and copying.

The existing operation counts record about 79 million unconditional jumps and
78 million switches in the MIR-level-3 artifact. They currently return to the
interpreter. The next bounded experiment is to absorb supported branch
terminators into JIT regions, preserving virtual instruction counts and
validating returned continuation indices. Guest calls, returns, and allocation
remain VM operations. Compare complete production-edit commands again before
keeping it. Frame/register storage remains a separate candidate; the sampling
result does not establish that zeroing dominates the runtime.
