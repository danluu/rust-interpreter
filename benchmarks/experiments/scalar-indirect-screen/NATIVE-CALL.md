# Native indirect transitions over the adopted scalar runtime

Candidate d712815d / VM1da74c27 passes631 workspace tests/profile,
431 Python controls (409 pass,22 skips),122 strict/cache commands and both
actual partial-artifact negatives. Closed disabled-indirect reconstruction
reproduces both adopted captures in full. Three candidate original profiles
retain exact logical counts, memory, entropy and code maps; scalar Call counts
are unchanged while native indirect execution removes interpreter re-entry.

Adopted df4006e0 uses identical exporter/wrapper. Native indirect execution is
explicit and candidate-only. Baseline/duplicate/candidate retain scalar calls
and matched cache/lookup settings. Historical anchor settings stay fixed.
This tests a new composition; earlier failed indirect screens remain parked.
