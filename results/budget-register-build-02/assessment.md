# Budget-register VM qualification

The isolated x22 ABI passes 293 workspace tests in debug and release, one ignored. Four new focused tests cover every instruction budget, native/internal entries, profiling and persistent registers, large register/ABI copies, and fault order. Existing host ABI and TLS tests pass.

Tool `36656766` uses VM `d0eb1143`; exporter and wrapper bytes are copied unchanged from qualified control `9637b0ac`. No production source or default changes. Broader real execution and complete-command performance gates remain pending.

Build 01 remains preserved: two new tests used exact error-string equality where the existing engines have different memory-fault wording. Build 02 recognizes only that established pair and strengthens repeated native-call and fault-order coverage; runtime errors were not altered.
