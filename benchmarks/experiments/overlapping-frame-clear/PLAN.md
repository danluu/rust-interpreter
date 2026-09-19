# Branch-free ordinary frame initialization with bounded overlapping stores

Start from24cd8e99: adopted production runtime plus closed test-only observers.
Scope ordinary-padding-scope02 confirms the actual typed ES8 hot frame is payload40,
alignment16, entered from caller extent153. Existing ordinary dynamic padding
clearing has22/19 byte-loop samples in797/609 generated self samples. All75/100
ES8 small dynamic-prefix sites satisfy P>=A. The earlier scalar-only and general
short-tail candidates remain parked; their code is not part of this candidate.

Keep the existing static empty-padding proof first. For remaining small frames
with power-of-two alignment A<=16 and A<=payload P<=256, clear P bytes beginning
at the old memory end, then A bytes ending at the complete new memory end.
For actual padding0<=p<A, intervals[old,old+P) and[old+P+p-A,old+P+p) overlap and
cover exactly the admitted P+p bytes. P>=A puts both starts within that range.
No extra backing, alignment assumption on the host pointer, discarded padding,
store before admission, change in bytecode charging or lazy checking is allowed.
Use the same fixed-store emitter and one STP/STUR tail. Ordinary scratchx11/x12
need no post-helper cursor contract; preserve all persistent/argument state.

Qualification: independent exhaustive integer/byte model across every eligible
payload/alignment/padding and16 host offsets, ineligible layout controls, then
native dirty-byte canaries/live registers including every payload0..257 plus513,
alignment1/2/4/8/16/32/64, all padding and16 host offsets. Expand full-VM repeated
dirty frame histories to alignments2/4/8 and the hot153/40 shape, with exact
instructions, peak memory and boundary resource errors versus interpreter.
Run existing clear/retained-history/protocol controls in debug and release.
Then full workspace verification and a release VM snapshot; exact5 entropy
record/replay workload pairs with per-PC/counter parity and code-span validation;
compose an explicit candidate tool. No default change until prospective real
changed-source ES8 screen and held-out comparisons pass their recorded gates.

Use owned .work/short-clear-tail-runtime-build01 target (actual hyphenated path
in controller), cap3GiB and admission max(14GiB,8GiB+2*allocated) before/after each
compiler child, two workers and shared45s lock. Preserve all failures/prefixes.
Freeze source/controllers through terminal and independent closure. No original
guest runs in this focused stage. Do not touch protected target, other sessions
or paused goal. Performance screens need their original fre16GiB admission.
