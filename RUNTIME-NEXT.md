# Next runtime work

See STATE.md for exact process identities, evidence and resource constraints.
The duration-order/template-history composition passed both parser gates but failed
its held-out fre token guard. All176 changed-source commands and strict controls
were correct. Median wall improvement2.94% is below the5.57% project A/A allowance;
no runtime adoption, later project guards or unchanged timing retry.

Preparation diagnostic02 is closed:192 original invocations,14878 observed hits,
no JIT declines. Ordinary emission falls from summed250ms to73ms; hot execution
still dominates. Both current normal-VM native-PC captures are closed and every
generated self PC is attributed. Copy/Call/Load dominate; scalar bodies are a
small category. See docs/SESSION-FRE-EXECUTION-20260919.md.

Memory subparts01 is closed:324 frozen inputs,19 artifacts, zero guest executions.
Load transfers and address selection dominate; frame-base calculations below1%
do not justify caching another host register. The earlier runtime composition
passed all five projects but narrowly failed the parser CPU guard. Review its
indirect/readonly/spill mechanisms with the current session implementation as a
new candidate, preserving all previous failures and requiring fresh qualification
and complete edited-source gates. Do not infer combined speedups from old ratios.
Main0620952a has the earlier closed diagnostics; publish the memory closure next.

No subagents or goal tools. Two workers, shared lock, dynamic disk checks, no
shared-target/peer cleanup. Continue indefinitely from measured evidence.
