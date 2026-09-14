# Transactional pending-region branches

Store each function's sorted leader/internal-entry records and a flat pending-edge
arena with per-target list heads. A region preparation verifies function identity,
leader ownership, exact declared local branch/fallback words and unique sites.
It resolves ready/self targets directly, queues only unresolved planned leaders,
and visits only the new region's incoming list. Unsupported targets retain tails.

Prepared holds an exclusive borrow of its metadata owner. All new words, patches
and edge-buffer growth are staged before code commit; growing the edge arena
copies old records into a temporary replacement only when capacity is insufficient.
Dropped/refused preparations leave owned capacity and lists untouched. The caller
supplies remaining aggregate metadata charge; local growth is also capped at
16 MiB including its own node/edge capacities and header. This component does not
yet supply the VM's aggregate ownership ledger.

Publish checks the same arena identity and expected append position, invokes the
qualified code transaction, then performs only reserved pushes and owned moves.
Stable old entries gain direct branches as targets appear. Native controls cover
fan-in, edge-buffer growth/drop, ready backward targets, metadata/code refusal,
malformed or duplicate declarations, stale/different arenas and duplicate region
publication. Self-loop encoding is checked without executing an unbudgeted loop.
Run all 360 bytecode controls in each profile and both exact saved captures.

No live demand loop or stable resume-table publisher is connected yet. Full
assertion/fault/budget/profile/TLS qualification and original changed-source timing
remain prerequisites for runtime adoption.
