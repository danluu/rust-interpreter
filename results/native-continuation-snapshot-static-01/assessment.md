# Static continuation and snapshot checks pass

Three controls pass in each build profile. Relocations use exact compiled resume
entries, convert word indices to arena-relative bytes, preserve the zero sentinel
for unsupported/one-past successors, and reject malformed records before any
word changes. Separate host assembler objects match 159 words per profile,
including all vector registers used by five full snapshot sizes and the new
continuation-field instructions. Neither object is executed.

No guest or generated code ran in this stage. Setup took 20.41 seconds across
the two commands. Closure verifies 222 frozen bindings and eight retained logs/
oracle artifacts. Native state-equivalence and whole-project qualification are
next; this establishes no performance result or adoption.
