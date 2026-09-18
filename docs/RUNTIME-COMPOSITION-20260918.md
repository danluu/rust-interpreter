# Runtime composition: parser guard rejects adoption

The September 18 native-indirect/readonly-scalar/successor-spill composition is
parked. It passed five project guards, but its complete incremental parser
history narrowly failed the predeclared CPU guard. The runtime delta is not
merged. The repository-profile parser successor remains unstarted; unchanged
measurements will not be repeated to seek a passing result.

These are complete changed-source build/test commands with strict type and
borrow checking. Each history has 15 valid edited pairs, duplicate controls,
intentional wrong edits and final source restoration. Original, wrong and
restored states are excluded from latency pairs. Two Cargo/prepared workers,
normal OS entropy and the 16 MiB JIT arena remain in use.

| Selected workload | Commands | Wall / adopted | CPU / adopted | Wall A/A | Wall / native |
| --- | ---: | ---: | ---: | ---: | ---: |
| fre token | 154 | 0.96769 | 0.96381 | 2.729% | 1.59822 |
| fre folded | 154 | 0.97865 | 0.98460 | 1.058% | 0.98478 |
| pgrust hashfn | 154 | 1.00314 | 1.00272 | 1.827% | 1.04814 |
| private rg-aot | 132 | 1.00143 | 1.00207 | 2.353% | 0.56641 |
| Nushell type-relations | 132 | 0.99991 | 0.99739 | 1.675% | 0.62011 |

The five project histories total 726 commands. Token improves 3.23% wall,
narrowly beyond its 2.729% control envelope; folded improves 2.13%. The other
three project cases establish no incremental speedup. Token and pgrust hashfn
are slower than ordinary native in these matched histories on the current
Apple M5 Max host; older hardware/run ratios are not substituted.

All 114 original parser compatibility tests and 16 protocol controls pass.
The separate 88-command incremental parser history also preserves every
original assertion, wrong-edit outcome, paired bytecode/catalog identity and
source restoration. Its timing guard is:

| Parser metric | Candidate / adopted | A/A envelope | Ratio plus envelope | Limit |
| --- | ---: | ---: | ---: | ---: |
| Wall | 0.996451919 | 0.048350074 | 1.044801992 | 1.05 |
| Child-tree CPU | 1.005400221 | 0.044817765 | 1.050217985 | 1.05 |

Wall passes; CPU fails by 0.000217985. This narrow engineering rejection is
not evidence of zero benefit or a confidently established regression. Keep the
threshold and the complete result. Parser candidate/native ratios are 1.34731
wall and 1.30603 CPU, so the native gap remains.

The final closure verifies 9,290 project inputs and the parser closure verifies
6,804 inputs plus 282 evidence files. It records `candidate_qualified: false`,
`parser_gates_passed: false` and the unstarted repository profile. Admission
lock timeouts and audit-only recoveries are retained; no completed guest
command or timing pair was repeated for closure. Qualified runtime components
and compiler work on main remain unchanged by this outcome publication.

Candidate tool `45a1529e` / VM `fd21a46f` was compared with adopted tool
`df4006e0` / VM `6ac4dd9e`, using the same exporter `cf4b3499` and wrapper
`45bca4f2`. These are selected-function/test-body workflows, not complete
application, libtest, unwinding, thread or general OS/FFI coverage. Next use
fresh native-PC samples of the adopted runtime to select a materially different
optimization; sample shares alone will not establish an end-to-end gain.

[Closed project evidence](https://github.com/danluu/rust-interpreter/tree/6dddcfb60129bf34297cb35c1a7f96069188fe11/results/runtime-composition-full-02),
[parser history and rejection](https://github.com/danluu/rust-interpreter/tree/6dddcfb60129bf34297cb35c1a7f96069188fe11/results/runtime-composition-parser-edits-incremental-01),
[terminal audit](https://github.com/danluu/rust-interpreter/tree/6dddcfb60129bf34297cb35c1a7f96069188fe11/results/runtime-composition-terminal-evidence-01).
