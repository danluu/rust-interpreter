# Qualify initialization after removing unreachable clone branches

The saved02 diagnostic repeats saved01's exact artifact bytes. All eight tried
signatures for each of token's two busiest precondition callees decline inside
the folder. Source inspection identifies an ordering problem worth testing:
the folder removes dead entry definitions using full CFG liveness, then asks
the conservative block initialization checker to inspect unreachable blocks.
Clone CFG cleanup is currently later, after that possible rejection.

Add a regression whose known argument selects a returning path while an
unreachable path reads an entry register. The original function proves complete
register initialization. After folding, the entry write becomes dead but the
unreachable reader can still reject the clone. First require the exact new
regression to fail on the current implementation, preserving its receipt.

Then move clone-only CFG cleanup before the final comparison against the
original function's initialization requirement. Keep global folding behavior
unchanged. Do not weaken the check or assume register zeroes: reject a clone
whose final body introduces register clearing. Maintain original function IDs,
ABI, frame memory writes, faults and the seeded entry/backedge certificate.

Host qualification floor: 4 GiB. Use the existing populated host target and
two workers. The focused before/after checks must run the exact regression,
then run378workspace tests per profile (one ignored). Re-transform the saved
original programs and measure the candidate only if it changes real artifacts.
All earlier low-gain results remain intact; no real-edit gate is relaxed.
