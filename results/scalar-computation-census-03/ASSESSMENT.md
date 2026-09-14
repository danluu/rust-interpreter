The saved-body census finds a larger opportunity in value-width information:
85,471,196 cast and 32,006,184 pack computations in successful token block scalar
Calls could be exact aliases. Exhaustive token has 192,968,201 cast and
61,479,669 pack computations; folded prefilter has 37,609 and 37,557. These
counts weight current live scalar computations with qualified original-PC hits.
They exclude failed private attempts and are not machine instruction savings.

All 137 source-qualified native bodies reconstruct exactly. The model's two
controls cover constant faults, overflow, byte joins and signed width bounds.
No guest ran and no executable guest code was published. No constant-only
computations were found. Duplicated multiply/result-overflow opportunities are
only 4,301,250 / 11,912,384 / 0 successful pairs; defer that isolated mechanism.

Next try bounded value-width aliasing in the native scalar emitter: redirect
only casts and single zero-offset packs whose complete value is proved equal
to an existing value. Keep original PCs, branch graph, steps and fault roots.
Retain the preceding dead-register emitter as an independent native reference,
qualify complete inputs/outputs and budget tails, then use the same prospective
changed-source primary. No runtime change is adopted from this census.
