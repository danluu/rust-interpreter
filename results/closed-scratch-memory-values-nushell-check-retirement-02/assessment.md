# Closed Nushell Cargo-check cache retired

Removed 2,687 nonexecutable compiler intermediates (1,635,401,672 logical bytes)
from the exact Cargo-check cache of the closed 132-command Nushell comparison.
All 9,574 protected hashes remain unchanged and every removed path is absent.
The 22 check commands, completed supervisor, source restoration, historical source
contents and open-file checks were verified. Native-test caches, executable
snapshots, source fixtures, timing traces and all raw benchmark proofs remain.

Recorded free space rose from 14,476,079,104 to 16,077,455,360 bytes; concurrent
activity prevents treating that difference as an exact physical reclaim figure.
The prior invalid-JSON source-fixture preflight refusal remains preserved and
removed nothing. The successful run hashes opaque fixtures without parsing them.

[Summary](summary.json), [closure](closure.json).
