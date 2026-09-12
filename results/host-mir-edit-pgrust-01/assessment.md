# Host dependency MIR: pgrust

All132 commands passed their expected outcomes, with 4 original tests, fifteen edited pairs, fifteen A/A pairs, wrong edits and compiled restoration. Candidate and baseline guest bytecode/catalogs match in every state.

The predeclared gate **passes**. Paired wall changes -0.13%; CPU -0.07%. Observed A/A envelopes are 2.50% wall and 2.37% CPU. These describe noise, not confidence intervals.

Candidate/ordinary-native paired wall ratio is 0.930; candidate/line-tables native is 0.957. All modes use two Cargo workers; native keeps default libtest concurrency.

| Custom mode | Command | CPU | Cargo | Frontend | Lowering | VM stage |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 0.546s | 0.533s | 0.454s | 0.016s | 0.009s | 0.022s |
| duplicate | 0.547s | 0.534s | 0.455s | 0.016s | 0.009s | 0.022s |
| candidate | 0.548s | 0.533s | 0.455s | 0.016s | 0.009s | 0.022s |

Complete-command ratios retain all15pairs. Stages are nested, and their separate medians need not add. Cargo unit intervals are rounded and may overlap; they are not CPU times or a measured critical path. Unit ratios use only reported matching intervals, with counts retained, and never change the complete-command gate.

Largest repeatedly reported unit groups, keeping Cargo target labels and features separate:

| Package and Cargo target label | Features | Baseline intervals | Candidate intervals | Paired ratio |
| --- | --- | ---: | ---: | ---: |
| hashfn  (check-test) | none | 0.040s | 0.040s | 1.000 |

A blank target label is preserved as reported; this table alone does not identify a host unit or prove where a flag took effect. The separate real Cargo qualification verifies the wrapper routing.

Initial empty-target observations and both rounded native suite/residual splits are retained in assessment.json. They are excluded from edited medians and do not establish a repeatable cold-build gain.

VM and exporter bytes are identical between custom arms; the wrapper is the candidate change. Broad adoption still requires the other predeclared project guards.

Tools: baseline `49746a2218dbfdccacac0031f47e7a13b0440489c226979ff3374f6f899e09f9`, duplicate `49746a2218dbfdccacac0031f47e7a13b0440489c226979ff3374f6f899e09f9`, candidate `466c60a2b833269591d014590e13811ffcc5efb8b91a3e667a041c40eaca2df5`.
