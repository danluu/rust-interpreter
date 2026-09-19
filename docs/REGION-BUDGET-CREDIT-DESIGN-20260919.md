# Forward-edge budget credit: implementation review

Status: diagnostic registered; no production change, build or guest execution.
The first admission expired while the other session held the shared lock. Its
receipt is closed with zero controls and cases. The unchanged diagnostic has a
separate readmission plan. Coverage must justify any implementation below.

The adopted resumable JIT already keeps the budget in x22. Ordinary regions use
four hot-path words: materialize cost, compare, branch on insufficient budget,
subtract cost. Calls and Returns have their own budget and state contracts.
The earlier scalar-copy-budget experiment changed individual guard instructions
and failed its primary. This proposal instead certifies forward native edges.

For a region, credit is its own cost plus the maximum credit of selected forward
successors. An edge is selected only within the same function, to an ordinary
compiled region with no range preflight. Backedges, calls, unsupported gaps and
guarded destinations cut the graph. A 4096-step cap cuts outgoing credit edges
when necessary. The certificate is a static inequality, not a sampled branch
assumption. An untaken successor never contributes an actual debit.

Each region retains a checked entry. Its external entry and resume-table entry
must lead there; ordinary Call returns also use it. A second entry, available
only through certified direct native edges, starts after the check and before
materializing/subtracting the original cost. The edge inequality guarantees that
this entry cannot underflow x22. No credit field or new register is needed.

The second entry cannot reuse x10 from its predecessor: intervening guest code
uses it as scratch. Checked regions therefore may need a second immediate.
Relative to the original four-word sequence, a checked visit costs one extra
word and a fast visit saves two. With that extra word charged to every affected
visit first, subtract three words per fast visit to obtain the nominal delta.
This bookkeeping includes costs; it is not a performance model for the CPU.

Implementation would need an unchanged-order region discovery/preparation pass.
`range_groups::runtime_plan` consumes a shared work budget; running it twice or
in a different order could alter existing admission. Compute each plan once in
the original order, retain it for emission, and derive credit from those exact
plans. A nonempty range plan emits root materialization, bounds checks and d16
setup. None may be bypassed. The current observer's absent RangeGuard span is a
diagnostic proxy, not the production eligibility API.

Current link records contain source word offset, successor PC and fallback.
They would also need the originating region identity to select the correct
entry. Scalar-call continuation links and native-tree links must stay checked.
Relocate only unpublished code and retain the checked fallback when no compiled
target exists. The whole-function code budget still decides publication. Code
maps must reconstruct all new entry offsets and spans exactly.

An insufficient larger guard returns before guest progress. The VM then follows
its existing single-instruction tail. This can increase fallback on small limits
and change native/interpreted counter partitions without changing successful
per-PC totals. Test every budget around both original costs and extended credit,
including short branches below the maximum, repeated loop backedges, external
entry at every region, calls, unsupported successors and range-guard declines.

The abstract Python oracle checks operation and fault prefixes, not native fault
cursor publication. Current native regions precharge their complete debit;
`Boundary::finish` validates remaining budget and commits extents before the
resumable runner reports a fault. A larger guard can choose the interpreter for
a region that the baseline would enter natively. Explicitly qualify memory,
assertion and arithmetic errors at all short budgets, complete state/extent
invariants and error order. Do not mistake abstract prefix equality for this
native proof. Keep strict frontend rejection and real unchanged assertions.

Proceed to a candidate only if saved coverage and its explicit costs support
the work. Then require typed/emitted-code/ABI qualification, original real-suite
profiles, a single fixed changed-source primary, and all required public,
private, parser and Nushell comparisons before adoption. Preserve failed gates;
no parameter sweep, unchanged retry or omitted guard is authorized by this note.
