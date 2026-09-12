# Token isolation passes; shared JIT code saves some setup but guest execution dominates

All 32 commands pass: 21 primary commands, seven independent checks and four
restored-source builds/runs. The same three original tests execute once in
native, fresh JIT and prepared JIT modes. The wrong edit fails the same original
assertions. Test source is unchanged, source restoration is verified, and all
14 primary plus two restored custom artifacts match across modes.

| Five edited commands | Median complete wall time |
| --- | ---: |
| Native build + three separate test processes | 2.092 s |
| Export + fresh JIT per test | 4.986 s |
| Export + shared prepared JIT | 4.838 s |

The median paired prepared/fresh ratios are 0.9686 wall and 0.9683 CPU. This is a
single cycle with five distinct edits, reported descriptively; it is not a
repeated confirmation or a default-promotion gate. The separate recorded-input
pilot established exact guest execution equality. These complete commands use
natural randomness, preserve original assertions, and do not pretend that
different random inputs must produce identical instruction counts.

Median execution is 3.311 s fresh and 3.162 s prepared. Constructor preparation
falls from 51.2 to 17.0 ms, and new compilation during the tests falls from
226.6 to 94.0 ms. Export/Cargo takes 1.556 and 1.532 s respectively. Native
builds take 1.080 s, and its three test processes total 0.984 s. Each figure is a
separate median of a nested scope; do not add them to reconstruct total time.
Reusing code removes duplicated work, but it does not close the guest-runtime
gap on this compute-heavy workload.

Cold original commands are 9.028 s native, 9.719 s fresh and 9.715 s prepared.
Each mode begins with a separate fresh target; tools and standard metadata are
prepared. Cold order is native/fresh/prepared and unbalanced. Native isolation
uses a process per test, unlike ordinary shared-process libtest, so these are
not interchangeable with previous ordinary-batch controls.

The optional runner remains available on main. Next measure the predeclared
folded-trie batch of eighteen tests and use those costs to guide broader suite
support. No ignored/should-panic/unwind/thread semantics are added by this work.

[Protocol](../../benchmarks/experiments/prepared-jit/WORKFLOWS.md),
[measurement](isolated-assessment.json), [verification](verification.json).
