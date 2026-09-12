Two independent real entropy streams reproduce exact results across the original fixed-clear VM and the combined VM, in both interpreter and JIT mode. Ten commands pass. Each stream contains three requests and 48 bytes; all replays consume the full tape.

The streams produce 13,345,253,023 and 13,345,235,287 instructions respectively, each with 8,161,249 bytes peak guest memory. Within each stream all five executions match exactly. Installed VMs and original bytecode are unchanged. This supports input nondeterminism as the cause of the earlier mismatch; it is a diagnostic on two streams, not a timing result or proof for every possible random input.

The stopped fresh-entropy comparison remains incomplete. Use explicit recorded inputs for its replacement while keeping the ordinary real-edit histories and their existing performance gates.
