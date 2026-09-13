# Memory and lookup composition: rg-aot

All132 commands have their expected outcomes, with1 original tests, fifteen edited pairs and fifteen A/A pairs. Custom bytecode and catalogs match for every state.

The prospective gate **passes**. Paired wall change -12.55%; CPU -11.53%. A/A envelopes: 2.46% wall, 1.61% CPU.

Candidate/ordinary-native wall ratio 0.396; candidate/line-tables native 0.414. All modes use two Cargo workers; native retains default libtest concurrency.

| Custom mode | Command | CPU | Std-MIR lookup | Cargo | Frontend | Lowering | VM |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 0.250s | 0.234s | 0.039s | 0.170s | 0.050s | 0.017s | 0.006s |
| duplicate | 0.251s | 0.234s | 0.038s | 0.170s | 0.050s | 0.017s | 0.006s |
| candidate | 0.219s | 0.207s | 0.006s | 0.172s | 0.050s | 0.017s | 0.006s |

All fifteen edited pairs, original assertions, wrong edits and restoration are retained. Stages are nested; separate medians need not add. A/A envelopes are descriptive, not confidence intervals. Initial empty-target observations are excluded and do not establish a repeatable cold-build gain.

Every edited candidate lookup is a validated cache hit. The candidate combines the qualified memory VM and cached identity lookup; the wide control uses fresh lookup. Exporter/wrapper bytes, strict checking and guest options match. These are composition results, not isolated component effects.

All declared project guards are required before adoption. Private names and command details remain local.
