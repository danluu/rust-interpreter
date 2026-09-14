# Initial native qualification finds a comparison identity mismatch

Debug completes with 347 passing controls, two failures and eleven ignored
diagnostics. Release remains unstarted. Both failures compare complete snapshots
from hint-enabled and hint-disabled emitters. Their new host-only continuation
fields hold different byte offsets because the two emitters have different code
lengths. Guest bytes, registers, frame fields other than the offset, and counters
match in the reported failures. The new snapshot overlap/ABI control passes.

Correct the test by requiring every nonzero offset, including one retained in a
popped descriptor, to equal that JIT's published caller/next-PC resume target.
Then compare those logical identities as well as all original snapshot state.
Do not merely discard the new field. Keep runtime and static-oracle source
unchanged; repeat native qualification after this substantive test correction.
The failed terminal and complete logs remain closed evidence.
