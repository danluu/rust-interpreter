# Lightweight wrapper reduces ordinary compiler routing overhead

Thirty rotated triples compared direct rustc, the heavy `78e60cdd` exporter
wrapper, and `c341296c`'s lightweight wrapper. All 90 measured commands returned
identical pinned compiler information without diagnostics. Median command times
were 12.739, 23.314 and 14.460 ms respectively. Median within-triple overhead
relative to direct rustc was **10.530 ms heavy versus 1.751 ms lightweight**;
the corresponding child CPU overhead was 9.987 versus 1.482 ms.

The resolver/version preparation, raw observations, rotation and executable
hashes are preserved. Every sample, including the first, is retained. Wall time
includes common active-command receipt publication. These are version probes
after previous compiler work, not a cold-loader or source-compilation benchmark.
Do not multiply the difference by unit counts and call that an end-to-end gain.
Actual edited and cold project commands determine retention separately.

[Exact inputs and samples](summary.json)
