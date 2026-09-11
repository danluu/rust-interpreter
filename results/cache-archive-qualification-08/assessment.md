# Archive regression checks with host selection

All 44 rejection checks and four existing coordinator scenarios pass, including
write/verification failures and interrupted retirement with successful recovery
from the verified archive. Both earlier archive formats restore successfully.
Hardlinks, bytes, timestamps, modes and the supported macOS attributes verify.
No real compiler cache is changed. Supervisor 81954/controller 81963 finished
successfully. The archive format and retirement mechanism are unchanged.

See [results](summary.json) and the separate
[host selector qualification](../host-cache-selector-03/assessment.md).
