# Toolchain lookup: pgrust

All132 commands have their expected outcomes, with4 original tests, fifteen edited pairs and fifteen A/A pairs. Custom bytecode and catalogs match for every state.

The prospective gate **passes**. Paired wall change -5.96%; CPU -5.16%. A/A envelopes: 1.52% wall, 1.43% CPU.

Candidate/ordinary-native wall ratio 0.887; candidate/line-tables native 0.881. All modes use two Cargo workers; native retains default libtest concurrency.

| Custom mode | Command | CPU | Std-MIR lookup | Cargo | Frontend | Lowering | VM |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 0.543s | 0.530s | 0.038s | 0.451s | 0.016s | 0.008s | 0.021s |
| duplicate | 0.533s | 0.522s | 0.038s | 0.442s | 0.016s | 0.008s | 0.022s |
| candidate | 0.510s | 0.502s | 0.006s | 0.455s | 0.016s | 0.008s | 0.022s |

All fifteen edited pairs, original assertions, wrong edits and restoration are retained. Stages are nested; separate medians need not add. A/A envelopes are descriptive, not confidence intervals. Initial empty-target observations are excluded and do not establish a repeatable cold-build gain.

Every edited candidate lookup is a validated cache hit. VM, exporter, wrapper, Cargo command and checking policy are identical between custom arms. This isolates launcher discovery; it establishes no guest runtime speedup.

All declared project guards are required before adoption.
