# Pending-region edge ownership qualifies

Source b36e737e passes all 360 bytecode controls per profile (13 ignored), then
reconstructs and independently reassembles both adopted captures exactly:
20,033/23,406 regions and 11,313,812/13,757,056 bytes. Four qualification commands
take 65.031200 seconds. The closure verifies 315 source/input bindings and ten
output artifacts. Original guest benchmarks remain unstarted.

Five new controls cover native fan-in resolution, transactional edge-buffer
growth/drop, ready backward edges, metadata/code-budget refusal with a successful
retry, malformed/duplicate sites, function ownership, stale/different arenas and
repeated publication. Native results and host ABI/SP match after each successful
change. Self-edge encoding is verified statically without executing an unbudgeted
loop. Declined transactions preserve code, pending heads and owned capacity.

Each function owns sorted leader records and a flat pending-edge arena with
per-target list heads. Preparation visits only the new target's incoming list,
resolves ready successors directly and stages unresolved edges and buffer growth.
An exclusive metadata borrow prevents intervening changes before code commit.
After the checked code transaction succeeds, metadata updates use reserved pushes
and owned moves only. Resolved edge slots remain charged initially.

This component accepts the caller's remaining aggregate metadata allowance and
also caps its local charge at 16 MiB. The VM's aggregate ledger, stable resume
slots, assertion publication and dispatch policy are not connected yet. No demand
execution or latency improvement is established. Connect those pieces next,
then qualify complete logical accounting and actual changed-source histories.
