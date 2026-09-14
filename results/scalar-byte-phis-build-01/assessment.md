# Isolated byte-phi immutable build passes

All 611 workspace tests pass in debug and release, with 13 ignored per profile.
Python discovers 429 tests: 407 pass and 22 declared compiler/native tests are
skipped. Four commands complete in 120.54 seconds.

Tool `7d80e36fe67ccc4a6a2c9e7cd244b828bb87fb5c23a4a1877601ff7e98dce1dd` contains VM
`a13ec48345224105fe058877fc819d8b2851300452c1b2b967b2c9d4b3c11c89` and the exact
adopted exporter/wrapper. The runtime change is contiguous byte-phi coalescing
from adopted source; parked read-only/store prototypes are absent. All build,
source and binary evidence is closed. No project timing is measured.

Proceed to strict checks, original profiles and the predeclared primary.
Main still uses df4006e0; passing build controls alone do not permit adoption.
