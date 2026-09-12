# Recorded whole-call stage costs

| Case | Inlining timer delta | Cargo delta | Execution delta | Command delta |
| --- | ---: | ---: | ---: | ---: |
| folded-literal-trie | +7.8 ms | +12.9 ms | -26.2 ms | -9.5 ms |
| token-phrase | +34.7 ms | +62.7 ms | -291.9 ms | -231.6 ms |

Paired stage medians are observations, not causal attribution, and need not sum to the command median. Original entropy and every pair remain. No new build, guest execution or changed gate.

The next investigation should examine scalar argument/result materialization at call boundaries. Existing native Calls already cross guest frames without returning to the Rust VM; simply adding native branches would repeat implemented work. Any new ABI needs typed eligibility, exact interpreter/JIT agreement and a new fixed end-to-end gate.
