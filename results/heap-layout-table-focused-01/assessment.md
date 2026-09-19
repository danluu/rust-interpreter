# Preserved controller-count failure

All three executed children returned0:16 heap tests/debug,16 heap tests/release,
and3 C allocator tests/debug. The controller then expected6 matches for the
c_allocator::tests:: filter, which excludes the three tests in the separate
allocation_budget_boundary_tests module. Runtime checks did not fail.

Focused02 retains and verifies these results. It runs only the missing3 debug
budget tests and all6 release C allocator tests. It does not rerun the completed
prefix, change runtime code, install a VM or execute/timing a guest.
