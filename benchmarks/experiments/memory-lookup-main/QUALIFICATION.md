# Complete-tool integration verification

Build source c458f40 passes 428 Rust tests per profile. Installed tool
e729a493 has exactly the measured VM99ceabaa and wrappercff204c5; its newly
built exporter is c1370fe6. Reuse the measured VM's seven exact selections,
nine suite commands and three per-PC profiles with explicit matching hashes.
The new exporter still needs current export/cache qualification.

Run the 98 declared root harness tests plus four project-driver tests. Freeze
the Python inputs and this directory before executing the Cargo checks.
Then run the existing 203-command cache/native matrix and the adapted
20-command native/fresh/cached Cargo fixture, with strict uncalled E0308 and
E0499 rejection. These are qualification, not timing comparisons.

Run 40 new-tool project commands: the first original state, wrong edit, all
five valid edits, then original-source restoration for each of Nushell,
private rg-aot, token, folded and pgrust. The corresponding retained reference
is cycle0 states0/-1/1..5 and cycle1 state0 from the completed comparison.
Token and folded original/restored bytecode can differ because allocation
addresses depend on edit history. A shorter edit sequence cannot simply use
the old final-cycle restoration artifact. Preserve the whole first-cycle
history so exact bytecode/catalog comparison remains meaningful.

Every command uses a fresh integration cache namespace and new report path.
Keep selection, limits, prepared workers, Cargo workers and guest rustflags
from its actual recorded argv/plan. Verify original assertion outcomes,
cache-hit routing, actual Cargo checking, source digests and exact artifacts.
Restore source on every exit. The driver rejects missing/duplicate output
options and any accidental reuse of reference output paths or tool keys.

Hold the shared lock with 45-second admission, reserve16GiB before starting,
and apply per-project cache estimates plus the8GiB per-command floor. No
other own build/test/profile runs concurrently. Preserve all completed
comparison caches and private source; publish only aggregate private receipts.

Only after these checks pass can source merge to main. Do not attach a new
performance verdict to these commands or rewrite any completed gate.
