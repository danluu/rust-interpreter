# Saved direct calls into large register frames

The conditional-demand parser policy failed despite reducing interpreted work.
Before changing initialization, use four exact adopted-VM profiles to weight each
callee's register/frame size by original direct-call counts. Conservatively
subtract all committed scalar completions per callee; scalar leaves avoid ordinary
frames. Preserve original logical-PC expansion and profile hashes.

Report functions above the current 65,536-register definite-initialization bound
and the largest nominal byte weights. These are potential direct-call storage
costs, not bytes proved cleared or timings: the fast initialization proofs can
already elide clearing. Unknown indirect/callback entries are outside the join.
Only a material weight warrants a typed census of actual initialization decisions
and why the current proof declines. Run no guest, change no runtime, keep the
shared lock and 8 GiB floor, and preserve all prior failed timing gates.
