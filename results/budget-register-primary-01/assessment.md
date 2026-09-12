# Budget-register primary decision

The fixed primary gates **fail**. Next: park the budget-register ABI; no threshold changes or tuning retries.

| Phase / case | Paired wall ratio | Paired CPU ratio | Native median | Control median | Candidate median |
| --- | ---: | ---: | ---: | ---: | ---: |
| aa / folded-literal-trie | 1.001141 | 1.001477 | 1.649s | 1.719s | 1.724s |
| aa / token-phrase | 0.999931 | 0.994515 | 2.046s | 4.571s | 4.571s |
| e2e / folded-literal-trie | 0.988390 | 0.981421 | 1.745s | 1.786s | 1.776s |
| e2e / token-phrase | 0.989873 | 0.983871 | 1.999s | 4.557s | 4.551s |

Each phase verifies 168 complete commands, 30 edited pairs and 84 artifact hashes. Original assertions, wrong edits, independent Cargo checks and source restoration remain. Both runtime tools use byte-identical exporter/wrapper binaries and corresponding bytecode.

Token requires at least 10% complete-command wall improvement, lower child CPU, and a gain greater than its fixed A/A envelope. Folded must stay within 5% wall and CPU regression. All A/A pairs and all regressions remain in the report.

Matched source-edit/build/test measurements on one host. A/A envelopes are descriptive, not confidence intervals; cycles and edit states are correlated. No fastest-native or whole-codebase compatibility claim.
