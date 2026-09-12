# Duplicate snapshot preservation

All 336 completed public snapshots retain their exact paths, bytes, modes, ownership and modification times. 312 duplicates now use independent APFS copy-on-write files. All eight original workflow verifications and 134 external hashes still pass.

Observed free space increased from 14,010,007,552 to 19,480,567,808 bytes during the operation; other host activity can affect that observation. No timing ran concurrently. Canonical files are unchanged; file identity, change and birth times of replaced duplicates can change. The fixture verifies independent writes in both directions and three failures that preserve originals.
