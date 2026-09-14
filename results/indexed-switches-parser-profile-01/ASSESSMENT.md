The original parser replay passes all assertions, selected-entry binding, exact
per-PC/backend counts, memory/entropy and native-code reconstruction. Logical
work remains 545,134,243 operations: 540,303,044 native and 4,831,199 interpreted,
including 72,085,625 scalar operations. Only switch lookup implementation changes.

All native words match after 1,230 bound scalar-Call address relocations account
for the 2,460 differing words. No unrelated instruction differs. One new guest
replayed the retained adopted entropy tape; 28 inputs and seven evidence files
are closed. Proceed to the preregistered changed-source primary; no speedup or
adoption follows from this correctness profile.
