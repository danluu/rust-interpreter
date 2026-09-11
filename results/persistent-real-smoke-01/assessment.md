# Persistent registers: original artifact smoke check

Source `d664bce`, tool `e89de7f8`, passes the original folded-trie and token test
artifacts with native calls, call stubs and persistent registers enabled. Both
baseline `b2aa6efe` executions also pass; all four commands return 0 and stdout
`0`. The saved artifact and binary hashes are frozen in [the receipt](summary.json).
This checks guest assertions and runtime coverage; it is not an E2E measurement.

Folded executes 4,138,403,285 virtual instructions in each mode. Token executes
13,369,460,863 baseline and 13,369,572,104 candidate instructions. Token consumes
guest random bytes and prior independent executions also have differing counts;
these runs do not prove identical traces or establish the cause of every count
difference. Guest-memory peaks match: 102,369 folded and 8,170,193 token bytes.
The deterministic workspace differential tests require exact counts and budgets.

The candidate publishes 100 ordinary/tree code instances with 128 persistent
register-pair assignments for folded, and 228 instances/332 pairs for token.
Three token analyses conservatively decline at their bounds. Successful outer
Call stubs execute 11,532,049 and 32,013,840 times, respectively. No unsupported
behavior or assertion was removed. The tools already pass all 240 workspace
tests in debug and release and ten CLI checks; repeated real edits remain next.
