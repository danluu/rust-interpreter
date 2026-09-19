# Extra namespace allowance

The current public controller uses 16 GiB initial admission for fre and 12 GiB for
pgrust, adding 2 GiB to the old seven-arm floors. This exceeds the approximately
0.2–0.5 GiB compiler namespace sizes observed in closed owned public caches and
leaves the existing 8 GiB per-child floor intact. This conservative addition
supersedes the prospective 14/10 GiB numbers in PLAN.md; it does not lower a gate.
Every child rechecks free space. The large/private adapters remain unimplemented.
