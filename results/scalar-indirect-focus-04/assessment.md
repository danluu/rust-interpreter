# Complete memory checks pass for the composed call boundary

All3 controls pass in both debug and release. Complete active linear and heap
bytes agree with the ordinary interpreter and adopted JIT on success and error
exits. Coverage includes cold and warmed indirect targets with scalar children,
null/readonly/overflow/heap/padding destinations, faults before and after external
writes, every instruction-budget tail and memory/depth limits. Original-PC
counts, result values and peak memory agree. The snapshot observer is test-only.
Closure verifies231 frozen inputs. The prior helper-import syntax failure is
separately retained; no tests ran in it. Proceed to the full immutable workspace
build; no original-project timing or adoption occurs yet.
