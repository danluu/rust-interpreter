# Actual CPU queries add 61 passing original tests

The custom runtime now executes a narrow, read-only macOS CPU-query primitive.
The refined candidate **59f64b2c** passes **303 original fre tests** against fresh
native controls, adding **61** to the prior 242. Another **17** stop at unavailable
TLS destructor registration, **7** are ignored and **62** hit the exporter's
10,000-instance expansion limit. All 320 ordinary exported bodies had fresh
native controls; all 320 native tests passed. Lowering and runtime refusals remain
separate from passing tests. [Fresh execution evidence](../audit-execution-fre-cpu-feature-02/summary.md).

The build remains an experimental coverage baseline. These results do not
establish faster edit/build/test commands or whole-application support.

The initial eleven-workflow comparison has now completed all **55 paired edits**
with identical bytecode and valid original-test/rejection controls. The candidate
wins **21/55** complete commands. Nushell's larger type-relation workflow loses
four of five pairs, adding **0.979 s** by the median paired difference, while its
guest execution changes by less than a millisecond. A completed repeat with Cargo
timing reports loses three of five pairs, adding 434 ms by the median paired
difference. Each edit rebuilds 19 units; most variation occurs before the selected
test target. The cause remains unresolved. Candidate 59f6 remains unselected.
[Full initial corpus](../paired-cpu-feature-corpus-01/summary.md).
[Completed diagnostic](../cpu-feature-nushell-diagnostic-01/summary.md).

The primitive recognizes a foreign `sysctlbyname` with a checked C ABI. The
runtime accepts bounded CPU-feature names and the exact `hw.cpufamily` request,
null write input, a four-byte value buffer and a separate eight-byte length
buffer. It validates guest memory, uses local host buffers for the actual OS
call, then copies back the actual status, value and returned length. Missing
features preserve the OS failure behavior; feature flags are not invented.
Other request names, buffer modes, writes and overlapping output buffers are
explicitly unsupported. Guest errno, general FFI, TLS destructors and native
unwinding remain unimplemented. Apple identifies `hw.cpufamily` as a read-only
integer query. [Apple's implementation](https://github.com/apple-oss-distributions/xnu/blob/main/bsd/kern/kern_mib.c),
[sysctl buffer contract](https://developer.apple.com/library/archive/documentation/System/Conceptual/ManPages_iPhoneOS/man3/sysctlbyname.3.html).

The initial candidate supported standard-library feature names but omitted
`hw.cpufamily`, which fre's own CPU detection also requests. Its real-code trial
kept 242 passing tests and stopped at that missing request in 62 others. The
refined VM reuses the exact same retained bytecode and has independent provenance;
61 pass and one now reaches TLS registration. Both trials are preserved.
[Initial trial](../audit-execution-fre-cpu-feature-01/summary.md),
[original collection](../lowering-audit-fre-cpu-feature-01/summary.md).

The opcode is appended to the V5 instruction enum. Existing opcode encodings
remain unchanged. Focused checks confirm that the new VM executes old V5
programs, while old VMs reject programs containing the new opcode. The custom
interpreter handles the checked host primitive; generated guest code still uses
the custom AArch64 emitter. No LLVM or existing guest interpreter fallback was
introduced. Type and borrow checking remain strict.

The candidate passes **92 bytecode tests**, **5,404 focused native/frontend
commands**, 24 leaf-option checks, 71 SIMD checks, 79 audit checks, 99 launcher
checks, 674 repeatability/native commands, **23,502 native differential/rejection
commands with leaf inlining off and another 23,502 with it on**, 76 unavailable-call
checks and 3,577 wide-pointer checks. Tests cover full integer CPU-family results,
missing features, constant/stack/heap names and buffers, ordinary Rust feature
detection, bad signatures, local homonyms, invalid memory, register aliasing,
live values across JIT boundaries, serialization and exact instruction budgets.
[Focused evidence](../cpu-feature-focused-03.json),
[broad correctness gates](../cpu-feature-default-validation-01.json).

All **18 original folded-literal-trie tests** pass together after five production
refactors, with unchanged original tests and an effective wrong-edit control in
all three engines. With explicit guest MIR3 and leaf inlining, median edited
commands take **1.768 s native, 3.941 s JIT and 21.619 s interpreted**. JIT loses
all five edited comparisons against native. Cold commands take 7.480, 7.979 and
25.965 s respectively, excluding reusable setup. The JIT's median execution stage
is 2.854 s and its median Cargo stage is 0.942 s; these separate medians need not
sum to the median complete command. This is a coverage gain with a substantial
remaining runtime cost. [Complete workflow](../e2e-workflow-fre-folded-literal-trie-cpu-feature-01/summary.md).

A separate 96-command regression screen uses identical old artifacts and both
VMs. All non-timing statistics agree. The six JIT cases have median paired changes
between −3.3 and +13.4 ms; interpreter controls have +83.4 and +74.3 ms median
paired changes. Those runtime measurements exclude Cargo and export. The completed
command comparisons above remain the selection metric.
[Runtime screen](../cpu-feature-runtime-01/summary.md).
