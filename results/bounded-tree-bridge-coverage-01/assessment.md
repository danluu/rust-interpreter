The current bounded-tree planner has enough protocol coverage to justify a
separate bridge prototype. It admits 37,089,088 / 66,403,920 block native calls
(55.85%) and 52,392,782 / 70,368,216 exhaustive native calls (74.45%). Their Call
spans account for 141 / 189 generated-code samples. Eligible returning functions
have another 54 / 86 samples, a separate upper bound because samples do not
identify the entering call path. These are opportunities, not time saved.

The exact planner admits 2,019 of 5,468 functions. Its five unchanged proof
controls pass in debug and release, including interpreter fixtures for sibling
padding and depth/storage bounds. Setup takes 3.14 seconds; typed analysis 0.82.
No benchmark executes and no machine code is generated or published.

Eligible calls split into 28,311,316 / 26,491,961 from ineligible callers and
8,777,772 / 25,900,821 from eligible callers. The latter are possible internal
tree edges; neither count is multiplied by a subtree size. Every observed
eligible call's plan fits the size of one current spare storage quota, but this
does not prove actual storage availability or readiness at the call.

The required closures contain 259 / 295 functions; 23 / 26 are absent from the
saved native captures. They must be prepared before bridge admission. Existing
captured code for the needed functions totals 1,042,372 / 1,114,060 bytes; these
are not the bridge's additional code sizes. Two eligible captured functions
already use guarded ranges. Their optimized bodies need an explicit compatible
fallback inside a complete tree, or a measured conservative exclusion. Do not
silently discard those optimizations or relax the default 16 MiB capacity.

The audit verifies 47 inputs and 174 Git bindings and reuses the two prior join
controls only after exact helper/test source checks. All native call totals and
transition samples reconcile. Raw typed plans, calls, missing dependencies and
sampled parts remain retained. Sample windows and bound-entropy profiles have
different scopes. Source identity remains tied to this experimental branch.

Next implement an explicit disabled bridge option. Admit complete trees before
progress using exact budget, depth, initialized storage and guest working-memory
bounds; otherwise execute the current Call. Keep frame clearing, argument/result
copy ordering, root/TLS behavior and fatal-error identity. Success must publish
exact counts and a normal caller continuation. The existing tree and resumable
cursor layouts, x22 meanings and host stack differ; they require adapters,
terminal-fault qualification and complete original-test/edit-command gates.
