# Shared scratch-value candidate scope

The same closed captures contain 45/15 data-load samples at existing eight-byte
Load opportunities and 45/29 at newly observed Copy opportunities. The combined
90/44 samples are disjoint (4.96%/2.97% of generated self samples). The separate
static counts are 2,655/3,071 Load sites and 2,930/3,461 Copy sites.

Copy availability was queried after original address handling. The older Load
observer queries before address formation, so its coverage is an upper estimate
until an implementation checks afterward. This is offline reuse of two partial
perturbed normal-entropy windows, not a new execution or speedup measurement.

Implement one bounded shared x9 cache for exact eight-byte local ranges in the
custom emitter. Query after address formation and keep all source/destination
validation, stores, high-half zeroing, logical budgets, profiles and fault exits.
Invalidate on unknown/overlapping writes, every possible x9 clobber and every
control transfer. Use fixed small metadata, no additional native registers or
guest-memory changes. Qualify against the interpreter and existing native path,
then use the original 40-command changed-source primary. These counts authorize
an experiment only; the current scalar runtime remains parked.
