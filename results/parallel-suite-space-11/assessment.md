The composed build's 4 GiB admission floor was not met after other workloads
used more disk. The completed folded-trie comparison's five compiler caches
were retired in space09, preserving executable and bytecode evidence; actual
free space increased by 1,320,116,224 bytes. The pgrust equivalent in space10
contained only 291,408 removable logical bytes and recovered 212,992 bytes.

Space11 extended the earlier retirement of five completed public Nushell audit
caches to their 1,025 nonexecutable `.rlib` files. Their previous inventory,
identities and hashes were verified before removal. All remaining files,
reports, source, native executables and dynamic libraries were preserved.
Actual free space increased by 1,737,998,432 bytes, to 5,861,453,824 bytes.
The completed space05 receipt describes what was retained at that time; its
rlib retention is superseded by this explicit, separately recorded cleanup.

Space08 stopped before any deletion because its proposed historical launcher
revision did not match the benchmark. Space09 uses the exact matching source
from aec01270cd480eaf10d24f37a8a482c11bc7b113. The unsuccessful preflight remains
under `.work/experiments/parallel-suite-space-08`; it is not a cleanup result.

No active workload, unresolved Nushell held-out cache, private cache, host
qualification cache or process was changed. These are storage maintenance
results, not interpreter performance improvements. The second composed build
then entered its debug qualification stage.
