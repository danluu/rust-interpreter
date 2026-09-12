The smaller-first schedule retains the same 32-million-unit global budget and
passes six offline transform/whole-artifact verification commands. Token declines
690 of 5,468 functions, versus 4,427 previously. Final token code has 1,245,554
operations versus 1,313,023 originally (5.14% fewer). The pass folds 34,282 value
operations and 1,501 switches and removes 79,246 dead register definitions before
CFG cleanup. Its diagnostic transformation time was 0.316 s.

Folded and pgrust output bytes are exactly the same as the prior schedule; their
budgets were not exhausted. Their final operation counts remain 263,508 and
7,387 (9.96% and 16.43% below the originals). All saved inputs remain unchanged.
These static reductions and host transformation times are not runtime savings.

The compiler passed 366 Rust tests in each build profile. Next qualify native
Rust fixture execution using the identical retained VM, then use the predeclared
actual edited-source command gate when project-workload disk admission permits.
No constant-folding runtime or compiler path has been merged to main.
