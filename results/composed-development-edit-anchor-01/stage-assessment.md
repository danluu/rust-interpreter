# Combined engine: anchor

All132 commands passed their expected outcomes: 3 original tests, fifteen valid edited pairs, fifteen A/A pairs, wrong edits and compiled restoration.

Predeclared performance gate **passes**. Median paired complete-command wall change -11.59%; CPU -11.58%. Descriptive A/A envelopes: 1.47% wall, 1.81% CPU. These are not confidence intervals.

Candidate/ordinary native paired wall ratio 1.911; candidate/line-tables native 2.117. Native uses default libtest concurrency; every mode uses two Cargo workers.

| Custom mode | Whole command | CPU | Cargo | Frontend | Lowering | VM execution stage |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 4.897s | 4.690s | 1.786s | 0.681s | 0.854s | 2.984s |
| duplicate | 4.829s | 4.628s | 1.773s | 0.687s | 0.870s | 3.008s |
| candidate | 4.298s | 4.104s | 1.650s | 0.696s | 0.721s | 2.580s |

Nested measured scopes; separate medians need not add. Native suite output is rounded; residual includes Cargo and process overhead.

Cache mode: reuse.
Median reused/lowered functions: 5180/195. Binding 0.157s, template decoding 0.044s, cache load 0.034s. These costs are nested within export; they are not additional whole-command time.

The initial fresh-cache commands are single observations, excluded from edited-pair medians. Their times and both native stage splits are retained in `stage-assessment.json`.

Tool keys: baseline `9637b0acb1d208524c3c8b446af64cfd5e2d0d3be75e1412a8df76750ce36223`, duplicate `9637b0acb1d208524c3c8b446af64cfd5e2d0d3be75e1412a8df76750ce36223`, candidate `8b16be8e49acbe0fd3c88ffadc9cef12282dab81b66dc3afca268d901796ea1e`.

Broader adoption still requires the other predeclared comparisons and held-outs.

Both custom routes use the original ordinary three-test batch, stopping at the first assertion. Separate outcomes after that failure are unavailable. This result does not measure prepared execution or parallel test scheduling.
