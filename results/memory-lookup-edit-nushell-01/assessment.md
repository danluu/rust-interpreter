# Memory and lookup composition: nushell

All132 commands have their expected outcomes, with14 original tests, fifteen edited pairs and fifteen A/A pairs. Custom bytecode and catalogs match for every state.

The prospective gate **passes**. Paired wall change -0.93%; CPU -0.60%. A/A envelopes: 5.73% wall, 2.23% CPU.

Candidate/ordinary-native wall ratio 0.629; candidate/line-tables native 0.653. All modes use two Cargo workers; native retains default libtest concurrency.

| Custom mode | Command | CPU | Std-MIR lookup | Cargo | Frontend | Lowering | VM |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 5.298s | 7.089s | 0.040s | 5.207s | 1.062s | 0.040s | 0.013s |
| duplicate | 5.355s | 7.307s | 0.040s | 5.263s | 1.060s | 0.041s | 0.013s |
| candidate | 5.317s | 7.012s | 0.006s | 5.260s | 1.098s | 0.040s | 0.013s |

All fifteen edited pairs, original assertions, wrong edits and restoration are retained. Stages are nested; separate medians need not add. A/A envelopes are descriptive, not confidence intervals. Initial empty-target observations are excluded and do not establish a repeatable cold-build gain.

Every edited candidate lookup is a validated cache hit. The candidate combines the qualified memory VM and cached identity lookup; the wide control uses fresh lookup. Exporter/wrapper bytes, strict checking and guest options match. These are composition results, not isolated component effects.

All declared project guards are required before adoption.
