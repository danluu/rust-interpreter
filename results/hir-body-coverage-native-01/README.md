# Body-v2 diagnostic native qualification

The separate public-rustc body diagnostic passed all 66 commands on its first
attempt. Complete native compiler outputs and execution outputs matched the
ordinary pinned compiler across original/body edit/earlier Unicode shift/
restoration, external trait-resolution edit/restoration, and four uncalled
error histories (type, move/borrow, const evaluation, constant panic). Exact
wrapper-path version and wrong-compiler rejection, version and dep-info-only
controls also passed. The two non-analysis probes never qualified coverage.

The original synthetic fixture has36 resolver owners and zero unexplained gaps.
Its17 structurally accepted bodies comprise12/19 free functions,3/3 inherent
methods,1/3 trait methods(two required/no-body),and1/1 trait-impl methods.
The same external-method body changes its input digest when its imported trait
changes Left→Right, and restoration restores its original digest. Actual native
outputs validate both external method choices. Bare external direct calls without
current legacy-const metadata proof remain rejected; indirect external function
values and external trait candidates are represented by current DefPathHashes.

This qualifies the structural diagnostic only. No actual HIR S/E IDs, cache
capture/replay effects, HIR cache hits, timing gain, Nushell coverage or holdout
result is established here. V1 remains unchanged. All328 public compiler input
files, complete loader guards and frozen source inputs were revalidated unchanged.
The archive retains full outputs, reports, commands/process receipts, fixture
histories and compiler/tool/source identity. Native binaries/caches remain local,
with artifact hashes retained. Source producer501d992e and driver/gate hashes
are recorded; successful qualification does not turn the earlier unrun contract
into a cache implementation.
