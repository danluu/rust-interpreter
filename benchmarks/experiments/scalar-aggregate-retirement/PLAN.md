# Retire the completed aggregate primary compiler intermediates

The aggregate primary is closed and parked after 40 commands. Free space is
about 11.7 GiB. Reuse the existing exact-root retirement protocol on its five
owned caches, with fresh closure, source-restoration, assertion, immutable
artifact, terminal, process and open-file checks under shared/invocation locks.
Only nonexecutable compiler intermediates are eligible. Protect every executable,
RBC, catalog, selection, timing report, raw log and evidence hash, and preserve
all shared targets, tools, source trees and private/peer caches. Record exact
identity before unlinking and verify protected hashes afterward. This is not
an automatic cleaner and does not alter the independent disk monitor.
