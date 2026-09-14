# Native store costs after the failed primary

Reconstruct every emitted scalar body in the three exact candidate profiles.
For store-bearing bodies, weight fixed store sites by original successful PC
counts. Count same-block containing prior stores, later same-block overwrites,
unneeded high lanes and unused logical-address snapshots. Retain the failed
candidate and all evidence; publish no guest code and run no guest timing.

These counts size implementation opportunities, not latency savings. They omit
private failures and require independent alias/fault/budget controls before
changing emission. Use the existing protected ROOT target, shared lock, two Cargo
workers, conservative initial disk admission and the 8 GiB child floor.
