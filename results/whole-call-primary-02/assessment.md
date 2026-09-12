# Whole-call primary decision

The fixed primary gates **fail**. Next: park bounded whole-call expansion; no threshold changes or tuning retries.

| Phase / case | Paired wall ratio | Paired CPU ratio | Native median | Control median | Candidate median |
| --- | ---: | ---: | ---: | ---: | ---: |
| aa / folded-literal-trie | 0.999899 | 0.998332 | 1.645s | 1.687s | 1.691s |
| aa / token-phrase | 1.002816 | 1.001873 | 1.984s | 4.454s | 4.467s |
| e2e / folded-literal-trie | 0.994355 | 0.992331 | 1.632s | 1.688s | 1.680s |
| e2e / token-phrase | 0.947729 | 0.950163 | 1.999s | 4.462s | 4.240s |

Each phase verifies 168 complete commands, 30 edited pairs and 84 artifact hashes. Original assertions, wrong edits, independent Cargo checks and source restoration remain. Both exact VMs/exporters are independently bound; the wrapper is identical. Corresponding bytecode must match in A/A only.

Token requires at least 10% complete-command wall improvement, lower child CPU, and a gain greater than its fixed A/A envelope. Folded must stay within 5% wall and CPU regression. All A/A pairs and all regressions remain in the report.

Matched source-edit/build/test measurements on one host. A/A envelopes are descriptive, not confidence intervals; cycles and edit states are correlated. No fastest-native or whole-codebase compatibility claim.
