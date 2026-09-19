# Actual miss-history diagnostic replay

Prerequisite closed25model/33integration tests perprofile and32featureoff controls.
Run original eight checked parser states in fresh and cached sessions, with the
same original114tests (1824total), wrong-edit failuretext, source artifacts and
runtime limits. Use unbuffered diagnostic digest binaries, two workers and strict
saved-input validation. No source compilation or acceptance timing.

Independently reconstruct each worker LRU from every attempted actual key. Require
zero dropped events, exact hit/miss membership, counter totals, storage entries,
charged bytes and cumulativeevictions after every request. Categories are prior
inserted key evicted, changed key for a previously attempted function, first
function on that worker, and previously attempted but never inserted. These
categories describe evidence, not causal code differences. Retain per-function
emission costs and native-word versus total insertion charges. No hypothetical
hit becomes executable or changes the actual policy. Featureoff remains unchanged.

Raw reports retain all events; compact summaries retain aggregates and most costly
misses. Every raw input/output is SHA-bound in closure. KernelCPU and ownerEOF/wait4
checked, no hidden retries. The model's transition/eviction/tamper tests precede
real suites. Lock45s,12GiBstart/8GiBchild, no goaltools or peerprocesscontrol.
