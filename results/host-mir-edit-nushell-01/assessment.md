# Host dependency MIR: nushell

All132 commands passed their expected outcomes, with 14 original tests, fifteen edited pairs, fifteen A/A pairs, wrong edits and compiled restoration. Candidate and baseline guest bytecode/catalogs match in every state.

The predeclared gate **does not pass**. Paired wall changes +0.35%; CPU +0.31%. Observed A/A envelopes are 4.13% wall and 1.68% CPU. These describe noise, not confidence intervals.

Candidate/ordinary-native paired wall ratio is 0.643; candidate/line-tables native is 0.653. All modes use two Cargo workers; native keeps default libtest concurrency.

| Custom mode | Command | CPU | Cargo | Frontend | Lowering | VM stage |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 5.019s | 6.754s | 4.926s | 1.018s | 0.040s | 0.012s |
| duplicate | 4.916s | 6.641s | 4.826s | 1.015s | 0.040s | 0.012s |
| candidate | 5.004s | 6.724s | 4.913s | 1.014s | 0.040s | 0.012s |

Complete-command ratios retain all15pairs. Stages are nested, and their separate medians need not add. Cargo unit intervals are rounded and may overlap; they are not CPU times or a measured critical path. Unit ratios use only reported matching intervals, with counts retained, and never change the complete-command gate.

Largest repeatedly reported unit groups, keeping Cargo target labels and features separate:

| Package and Cargo target label | Features | Baseline intervals | Candidate intervals | Paired ratio |
| --- | --- | ---: | ---: | ---: |
| nu-protocol (blank label) | os, os_pipe | 1.610s | 1.590s | 0.991 |
| nu-protocol  (check-test) | default, os, os_pipe | 1.180s | 1.170s | 1.017 |
| nu-protocol  (check) | default, os, os_pipe | 1.160s | 1.170s | 1.026 |
| nu-command  (check) | aegis-password-generator, crossterm, getrandom, js, notify-debouncer-full, open, os, os_pipe, rand, reedline, uu_cp, uu_mkdir, uu_mktemp, uu_mv, uu_touch, uu_uname, uu_whoami, uuid, which | 0.950s | 0.940s | 1.000 |
| nu-cmd-extra  build-script | none | 0.270s | 0.260s | 0.964 |
| nu-parser  (check) | none | 0.230s | 0.220s | 1.000 |
| nu-cmd-extra  build-script (run) | none | 0.220s | 0.220s | 1.000 |
| nu-cli  (check) | none | 0.210s | 0.220s | 1.000 |

A blank target label is preserved as reported; this table alone does not identify a host unit or prove where a flag took effect. The separate real Cargo qualification verifies the wrapper routing.

Initial empty-target observations and both rounded native suite/residual splits are retained in assessment.json. They are excluded from edited medians and do not establish a repeatable cold-build gain.

VM and exporter bytes are identical between custom arms; the wrapper is the candidate change. Broad adoption still requires the other predeclared project guards.

Tools: baseline `49746a2218dbfdccacac0031f47e7a13b0440489c226979ff3374f6f899e09f9`, duplicate `49746a2218dbfdccacac0031f47e7a13b0440489c226979ff3374f6f899e09f9`, candidate `466c60a2b833269591d014590e13811ffcc5efb8b91a3e667a041c40eaca2df5`.
