# Selective register repair: closed result

The selective interpreter-repair variant passes correctness qualification but
does not improve the changed-source primary. Main retains the adopted custom
scratch/scalar JIT. No larger comparison or unchanged retry follows.

The prior implicit-zero prototype normalized every proven-narrow register read
before interpreting it. This variant skips normalization where the actual
consumer first truncates or masks the value. It retains full repairs for
checked function handles, TLS,128-bit operations and unreviewed helpers.
A typed census reduces eligible repair operands from6.54M to1.03M and8.51M
to0.84M in the two original token tests. These are operation counts, not time.
Strict type/borrow checks, guest initialization, limits and fault rules remain.

All634Rust tests/profile and427Python tests pass (16ignored Rust observers,
22Python skips), as do121strict/cache commands and three original profiles.
Logical PCs, memory peaks and entropy match adopted df4006e0. Native layouts,
execution distributions and bytes match parked3e53b127 except verified address
immediates at427/532/21scalar Call sites. The observer initially mishandled
operand-rendered Call labels; its failure and successful first guest are retained.
The corrected observer reused that capture and ran only the two unstarted guests.

The40-command fre token history includes original source, a deliberately wrong
edit, five valid edits and restoration across twelve original tests. All expected
outcomes, source restoration and current-arm bytecode identities pass. Median
paired wall ratio1.011454947 is1.15% slower than adopted; CPUratio0.998580341
is nearly unchanged. A/A variation is1.78% wall and1.09% CPU. The wall
margin1.029269619 fails; CPUmargin1.009444555 passes. Candidate/native wall
ratio is1.609743254. This does not establish a benefit or isolate the cost of
selective repair against the separately timed conservative prototype.

Tool6c26c1c8 /VM610a3574 and the unchanged adopted compiler components remain
archived on `experiment/selective-narrow-repair-20260918`. The closure verifies
1,674evidence files and56artifacts. [Full result and qualification](https://github.com/danluu/rust-interpreter/blob/1ccd6f16/results/selective-narrow-repair-screen-token-01/ASSESSMENT.md).

Next inspect JIT preparation costs in saved real edit histories. PreparedJit
already reuses compiled code inside each suite worker; any cross-process reuse
proposal must target remaining work and pay for identity checks, relocation and
I/O. Compiler/Cargo ownership remains separate. This engine still covers
selected functions/test bodies, with incomplete full-application thread, unwind
and operating-system support.
