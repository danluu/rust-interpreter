# Prove reads are preceded by frame writes

Baseline source: main `8faae61`, including the qualified general interpreter
changes. The saved es8 artifact and same-process native samples still describe
the historical `9637b0ac` tool; the proof does not execute or alter that artifact.

First implement a diagnostic, bounded proof in this existing experiment crate.
Track byte initialization from argument slots and explicit local stores/copies
within each basic block. Reset pointer facts and nonargument initialization at
every block boundary, including backedges and unreachable blocks. Check reads
before writes, including aliased operands and return-slot padding. Unknown
pointer reads and unknown memory effects require the whole allocated frame to
have been initialized. Preserve the one allocated byte of zero-sized frames.
Decline oversized analyses and exhaustion of an explicit work budget.

A call is a candidate only if both the callee proof and the existing typed
caller-local argument-source proof pass. Skipping callee clearing otherwise
changes arguments that alias the new frame. Alignment padding, register
initialization, entry/TLS frames, bounds faults and instruction charging are
outside this diagnostic's proposed change. Bytecode V5 and runtime defaults
remain unchanged.

Test local partial reads, return padding, unknown pointers, pointer-register
overwrites, overlapping copies, skipped definitions, loops, zero-sized frames,
call-source aliases and proof limits. Then join the typed call identities to
the retained es8 clearing samples using the existing exact instruction-sequence
and arena attribution. Report declined hot callees as well as eligible ones.
Record hashes, diagnostic build configuration and terminal command outcomes.

Proceed to runtime implementation only if that census exposes enough removable
work to plausibly justify the established 8% command-time screening threshold.
Sample shares are a bound on the opportunity, not a predicted speedup. If the
conservative proof covers little clearing, inspect the dominant decline reason
before choosing a stronger proof or another direction. Any implementation must
preserve strict rustc checks, assertions, exact limits, faults and TLS, pass
differential tests, and win a real edit/build/test comparison before promotion.
