# Nushell qualification passes; first timing is slower

The new compiler wrapper passed all fourteen original type-relation tests after
the generic `Type::list` API edit. Nine primary commands, three independent
checks and six matching paired artifacts verify. The wrong edit failed in all
three modes. All ten frozen inputs matched, source was restored, and the six
custom launch records named the expected verified heavy/lightweight wrapper.

| Complete command | Native | Heavy wrapper, 78 | Lightweight wrapper, c341 |
| --- | ---: | ---: | ---: |
| Target-cache-cold original | 48.017 s | 75.020 s | 78.169 s |
| Generic API edit | 11.020 s | 5.063 s | 5.219 s |
| Edited child CPU | 34.034 s | 7.117 s | 7.217 s |

The independent edited Cargo-check command took 4.405 s. These are single
qualification observations. The candidate was slower here despite its lower
version-probe startup cost. This observation is preserved and does not support
retention. Repeated warm edits and fresh-target cold comparisons with balanced
mode order are needed to measure the actual pipeline effect on this host.

Both custom modes use the same VM binary, ordinary JIT with resumable/persistent
calls off, matched leaf inlining, std-MIR and strict checking. Native uses root
O0/incremental, eighteen build jobs and default test concurrency; custom builds
use four jobs. Cold excludes toolchain/dependency fetching, std-MIR setup and
OS cache clearing. The earlier runtime gates remain separate and failed.

[Complete records](summary.json) · [Verification](verification.json)
