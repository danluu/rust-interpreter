# Reclaim the completed Nushell ordinary-native compiler intermediates

Aggregate cleanup leaves about13.6 GiB, below ROOT's14 GiB Rust build admission.
The ROOT-owned native cache from closed `scratch-memory-values-edit-nushell-01`
still occupies about5.7 GiB. Its separate native-lines cache is already retired;
do not revisit it. Apply the same exact-history retirement policy to only the
ordinary-native cache, validating all132 commands, the22 native original/wrong/
valid/restored commands, full726-command closure, source restoration, historical
source objects and retained artifact hashes before inventory. The source and
all histories remain retained; only nonexecutable compiler intermediates go.

Preserve every executable, bytecode, catalog, timing report, raw log, source,
shared build target, installed tool and private/peer cache. Check recorded
processes and current open files under the shared lock, inventory exact file
identities before unlinking and verify every protected hash and frozen input
afterward. Native artifacts support replay and inspection without these unused
compiler intermediates. Do not alter the independent disk cleaner. No build,
guest execution or timing comparison occurs;8 GiB floor/admission.
