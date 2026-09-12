# Native stage attribution from retained commands

Parsed the original stdout for all 135 successful edited native commands. No builds or tests were rerun. These are the same histories as STATUS, with each row retaining its own controls.

| Workflow | Native command | Native suite | Outside suite | Custom Cargo | Custom execution |
| --- | ---: | ---: | ---: | ---: | ---: |
| folded-literal-trie | 1.702s | 0.30s | 1.388–1.398s | 0.851s | 0.772s |
| token-phrase | 1.965s | 0.61s | 1.350–1.360s | 1.476s | 2.899s |
| nushell-type-relations | 7.529s | 0.00s | 7.524–7.529s | 3.986s | 0.011s |
| ruff | 5.259s | 0.01s | 5.244–5.254s | 2.861s | 0.069s |
| nushell | 0.657s | 0.00s | 0.652–0.657s | 0.370s | 0.006s |
| forward-anchored-tls | 1.510s | 0.10s | 1.395–1.405s | 0.805s | 0.134s |
| pgrust-sha1-inline8 | 0.810s | 0.12s | 0.685–0.695s | 0.445s | 0.131s |
| pgrust | 0.678s | 0.00s | 0.673–0.678s | 0.424s | 0.017s |
| rg-aot | 0.564s | 0.00s | 0.559–0.564s | 0.154s | 0.005s |

The native harnesses report rounded suite duration; 0.00s means an interval from zero to about 5ms. Nushell type-relations uses a grouped harness; the other rows use libtest. Outside-suite time is a residual, not pure compile time. Custom execution includes VM startup and JIT compilation, so these execution columns are not identical scopes. Per-stage medians need not sum to command medians.

This narrows the hybrid question to Cargo targets. Selecting native tests still requires compiling their library-test executable. A per-test runtime threshold that omits that cost is not a valid command-time estimate. The current batch records do not contain per-test guest times or a qualified shared native/export compilation path, so they cannot establish a mixed-test policy or a never-slower guarantee.
