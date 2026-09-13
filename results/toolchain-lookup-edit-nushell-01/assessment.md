# Toolchain lookup: nushell

All132 commands have their expected outcomes, with14 original tests, fifteen edited pairs and fifteen A/A pairs. Custom bytecode and catalogs match for every state.

The prospective gate **does not pass**. Paired wall change -0.54%; CPU -0.91%. A/A envelopes: 6.56% wall, 2.73% CPU.

Candidate/ordinary-native wall ratio 0.561; candidate/line-tables native 0.637. All modes use two Cargo workers; native retains default libtest concurrency.

| Custom mode | Command | CPU | Std-MIR lookup | Cargo | Frontend | Lowering | VM |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 5.386s | 6.722s | 0.039s | 5.290s | 1.080s | 0.040s | 0.012s |
| duplicate | 5.721s | 6.797s | 0.038s | 5.633s | 1.073s | 0.041s | 0.012s |
| candidate | 5.568s | 6.662s | 0.007s | 5.509s | 1.080s | 0.041s | 0.012s |

All fifteen edited pairs, original assertions, wrong edits and restoration are retained. Stages are nested; separate medians need not add. A/A envelopes are descriptive, not confidence intervals. Initial empty-target observations are excluded and do not establish a repeatable cold-build gain.

Every edited candidate lookup is a validated cache hit. VM, exporter, wrapper, Cargo command and checking policy are identical between custom arms. This isolates launcher discovery; it establishes no guest runtime speedup.

All declared project guards are required before adoption.
