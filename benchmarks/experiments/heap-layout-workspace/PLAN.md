# Whole-workspace qualification for the heap layout table

Do not launch before the separately closed focused gate proves16 heap controls
(including the unchanged tree reference) and6 C allocator controls per profile.
Bind exactly those runtime sources. Relative to adopted fca687eb, only Cargo's
feature declaration, heap.rs's layout-table alias, the exact test-only reference
and four differential controls may differ.

Four commands:468 discovered Python tests (446pass,22skip), complete feature-enabled
Rust workspace in debug and release (618pass,13ignored per profile), then a
feature-enabled ordinary VM build retained with its exact hash. Runtime/native
fixtures stay at two test workers and Cargo builds at two jobs. Preserve known
scratch/native-copy/scalar-call regressions and the new allocator controls.
No original project guest, source edit, native timing or installation runs here.

Recompute conservative build admission before each child:
max(14GiB,8GiB+2*allocated shared target). Shared benchmark lock45s, child8GiB.
Freeze all source/scripts/tests and retained focused evidence through independent
terminal/source/log/output closure. Preserve any completed prefix on failure;
never rerun passing commands just to repair reporting or disk admission.
