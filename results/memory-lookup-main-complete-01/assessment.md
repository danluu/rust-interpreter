# Qualified memory/lookup integration

The complete source integration passes428 Rust tests per debug/release profile
(one ignored),104 Python harness tests,223 cache/native/Cargo commands and40
real-project history commands across Nushell, private rg-aot, fre token, fre
folded and pgrust. Original, wrong, five valid edited and restored states
match retained bytecode, catalogs and assertion outcomes. All sources are
restored; current frozen inputs and terminal receipts are verified.

Tool `e729a493` contains the exact measured VM `99ceabaa` and wrapper
`cff204c5`, so its seven exact selections, nine suite commands and three
per-PC/memory/entropy profiles are reused by binary identity. The rebuilt
exporter `c1370fe6` is separately identified and received the new export checks.
No guest backend fallback or lazy type/borrow checking was introduced.

Two driver failures remain recorded. A missing retained cache protocol stopped
before fixture commands; restoring it allowed the223 checks to run. A catalog
field-name mismatch stopped project qualification after16 completed large/
private commands and one token original command. Both token artifacts matched
in the post-failure audit. A tested adapter fix completed the remaining24
commands in fresh namespaces, preserving all16 successful commands and the
extra original observation. Neither failure was a guest result mismatch.

This is correctness qualification, not another timing comparison. The
[726-command composition](../memory-lookup-complete-01/assessment.md) remains
the performance evidence: token wall improves18.35% against the fixed anchor
and7.66% against the wide runtime, while still taking1.894 times ordinary
native Cargo. All five prospective gates pass; the small Nushell/folded
incremental changes are within observed noise. Historical failed component
decisions remain unchanged. Runtime/cache options remain explicit.

[Exact proof and hashes](summary.json),
[qualification protocol](../../benchmarks/experiments/memory-lookup-main/QUALIFICATION.md),
[new suggestions review](../../docs/SUGGESTIONS-REVIEW-20260912-2210.md).
