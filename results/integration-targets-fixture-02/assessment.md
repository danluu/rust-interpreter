# Shared integration dependency cache qualified

All 14 actual commands pass the expected controls: five native and nine custom.
Target A and B share one Cargo dependency cache, retain distinct bytecode
sidecars, and A executes correctly after B fails its different assertion.
The existing library route keeps its original cache. Wrong production code and
uncalled type/borrow errors remain rejected; restoration succeeds.

Source: `759bbbc`, branch `experiment/test-targets`; guest tools remain
`9637b0ac`. Four target-selection unit checks also pass. This is fixture
correctness evidence; the original fre integration targets are the next check.
