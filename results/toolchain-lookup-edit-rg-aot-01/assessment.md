# Toolchain lookup: rg-aot

All132 commands have their expected outcomes, with1 original tests, fifteen edited pairs and fifteen A/A pairs. Custom bytecode and catalogs match for every state.

The prospective gate **does not pass**. Paired wall change -13.18%; CPU -11.67%. A/A envelopes: 3.24% wall, 3.67% CPU.

Candidate/ordinary-native wall ratio 0.397; candidate/line-tables native 0.415. All modes use two Cargo workers; native retains default libtest concurrency.

| Custom mode | Command | CPU | Std-MIR lookup | Cargo | Frontend | Lowering | VM |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 0.248s | 0.233s | 0.039s | 0.166s | 0.049s | 0.017s | 0.006s |
| duplicate | 0.250s | 0.234s | 0.040s | 0.167s | 0.048s | 0.017s | 0.006s |
| candidate | 0.218s | 0.202s | 0.006s | 0.167s | 0.048s | 0.017s | 0.006s |

All fifteen edited pairs, original assertions, wrong edits and restoration are retained. Stages are nested; separate medians need not add. A/A envelopes are descriptive, not confidence intervals. Initial empty-target observations are excluded and do not establish a repeatable cold-build gain.

Every edited candidate lookup is a validated cache hit. VM, exporter, wrapper, Cargo command and checking policy are identical between custom arms. This isolates launcher discovery; it establishes no guest runtime speedup.

All declared project guards are required before adoption. Private names and command details remain local.
