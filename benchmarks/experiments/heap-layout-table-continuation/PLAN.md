# Complete the allocator controls without repeating the passed prefix

Focused01 passed16 heap controls in each profile and3 C allocator controls in
debug, then stopped on its incorrect expectation of6 matches for the narrower
c_allocator::tests:: filter. The other3 are in allocation_budget_boundary_tests.
Its terminal, source and logs are independently closed and remain unchanged.

Focused02 verifies that entire closed prefix and runs only the missing debug
allocation-budget module (3) and all release C allocator controls (6). It then
reports the combined16 heap and6 C allocator controls per profile. No runtime
source changes, guest execution, installation or timing. Recompute the original
conservative build floor before each child; shared lock45s and2workers. Freeze
sources through independent closure. The full workspace gate consumes this
combined receipt and continues to require618 Rust passes and13 ignored/profile.
