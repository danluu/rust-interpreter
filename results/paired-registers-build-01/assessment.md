# Paired register-transfer host qualification

All 421 debug and 421 release tests pass, with one ignored per profile. The
new tests check exact pair encodings and instruction counts at offset
boundaries, both halves of nontrivial values across VM exits, ordinary and
resumable execution, persistent registers on/off and every instruction-budget
tail. The first build passed; no failed run or reused test result is omitted.

The candidate restores the qualified wide-operation runtime and changes only
register spills and persistent reloads, retaining the exact f871 exporter and
wrapper. It does not include guarded indirect-call specialization. Seven
exact real tests, nine suite commands, strict native/cache controls and current
profile comparisons remain required before any performance measurement.
