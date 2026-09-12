# Combined engine: pgrust

All132 commands passed their expected outcomes: 4 original tests, fifteen valid edited pairs, fifteen A/A pairs, wrong edits and compiled restoration.

Predeclared performance gate **passes**. Median paired complete-command wall change +0.18%; CPU +0.97%. Descriptive A/A envelopes: 2.38% wall, 1.56% CPU. These are not confidence intervals.

Candidate/ordinary native paired wall ratio 0.942; candidate/line-tables native 0.907. Native uses default libtest concurrency; every mode uses two Cargo workers.

| Custom mode | Whole command | CPU | Cargo | Frontend | Lowering | VM execution stage |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 0.546s | 0.532s | 0.456s | 0.017s | 0.009s | 0.017s |
| duplicate | 0.549s | 0.537s | 0.457s | 0.017s | 0.009s | 0.017s |
| candidate | 0.550s | 0.537s | 0.454s | 0.017s | 0.009s | 0.022s |

Nested measured scopes; separate medians need not add. Native suite output is rounded; residual includes Cargo and process overhead.

Cache mode: off.

The initial fresh-cache commands are single observations, excluded from edited-pair medians. Their times and both native stage splits are retained in `stage-assessment.json`.

Tool keys: baseline `fe9dcae0c86c6df0b6ac629034bab3a291e15e5315f9bfc87f5da9cbb4d0fe6e`, duplicate `fe9dcae0c86c6df0b6ac629034bab3a291e15e5315f9bfc87f5da9cbb4d0fe6e`, candidate `9abacd0a72846d7721771b4a48c63f6178eb15f272698dd243404a395e3b6f2b`.

Broader adoption still requires the other predeclared comparisons and held-outs.
