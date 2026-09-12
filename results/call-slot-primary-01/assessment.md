# Guarded Call primary decision

The fixed primary gates **fail**. Next: park guarded Call arguments; no threshold changes or tuning retries.

| Phase / case | Paired wall ratio | Paired CPU ratio | Native median | Control median | Candidate median |
| --- | ---: | ---: | ---: | ---: | ---: |
| aa / folded-literal-trie | 1.007006 | 1.005184 | 1.646s | 1.718s | 1.728s |
| aa / token-phrase | 1.001059 | 1.000221 | 1.991s | 4.510s | 4.521s |
| e2e / folded-literal-trie | 0.986095 | 0.994460 | 1.664s | 1.729s | 1.721s |
| e2e / token-phrase | 0.987324 | 0.988768 | 2.015s | 4.544s | 4.478s |

Each phase verifies 168 complete commands, 30 edited pairs and 84 artifact hashes. Original assertions, wrong edits, independent Cargo checks and source restoration remain. Both runtime tools use byte-identical exporter/wrapper binaries and corresponding bytecode.

Token requires at least 10% complete-command wall improvement, lower child CPU, and a gain greater than its fixed A/A envelope. Folded must stay within 5% wall and CPU regression. All A/A pairs and all regressions remain in the report.

Matched source-edit/build/test measurements on one host. A/A envelopes are descriptive, not confidence intervals; cycles and edit states are correlated. No fastest-native or whole-codebase compatibility claim.
