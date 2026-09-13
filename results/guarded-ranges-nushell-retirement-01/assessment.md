# Completed-cache recheck, no reclamation

The six exact public cache roots from the adopted memory/lookup Nushell
comparison contain no remaining eligible compiler intermediates. They had
already been retired by the earlier public-cache and native-dependency cleanup.
This recheck removed zero files and reclaimed zero bytes. It should not have
been proposed as new headroom without reconciling that earlier inventory.

All28,509 protected hashes remain unchanged under the shared and namespace
locks. No private cache or other session was touched. Preserve this zero-work
receipt and exclude these six roots from future reclamation estimates. The
full harness can proceed with current space; Nushell itself still requires
its separate higher admission threshold before any command starts.
