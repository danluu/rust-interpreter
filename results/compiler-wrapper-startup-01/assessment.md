# Cost of the current compiler wrapper

Thirty rotated triples ran the resolved pinned rustc's `-vV` directly, through
the original b2 exporter, and through the current 78 exporter. All 90 measured
commands returned identical compiler information without diagnostics. Two
preparation commands resolved and identified the compiler. Installed executable
hashes and diagnostic inputs were checked before and after the run.

Median command times were 11.783 ms direct, 21.535 ms through b2, and 21.575 ms
through 78. Median within-triple overhead was 9.661 ms and 9.655 ms respectively.
The raw observations include every sample and child-tree CPU accounting.
Wall timing includes the common active-command receipt publication.

This is an ordinary-rustc routing diagnostic after prior compiler work. It does
not compile a crate, measure cold dynamic-library loading, exercise std-MIR
argument transformation, or prove that multiplying these deltas by Cargo unit
counts predicts a build-time gain. The source confirms the heavy exporter loads
rustc_driver and starts another rustc for unselected units. A lightweight exec
wrapper is worth a separate experiment, particularly with hundreds of cold
dependency units. The 19-unit warm Nushell graph still contains seconds of real
checking and build work; routing cannot eliminate that work.

[Exact binaries, commands and samples](summary.json)
