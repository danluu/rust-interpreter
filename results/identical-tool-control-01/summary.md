# Identical-tool production-edit control

These differences occur with identical installed tools and guest artifacts. They demonstrate variation in this control, not the size or cause of any candidate effect. The sequence includes unequal numbers of intervening commands since each cache was previously used; counts alone do not establish a cache mechanism. Shared binary paths and only five edited pairs limit inference.

| Edit | Retained in baseline slot | Retained in candidate slot | Difference | Intervening commands, baseline/candidate |
| --- | ---: | ---: | ---: | ---: |
| 1 | 6.418 s | 6.599 s | +181.0 ms | 2 / 4 |
| 2 | 6.759 s | 6.530 s | -228.6 ms | 3 / 1 |
| 3 | 5.962 s | 7.246 s | +1284.2 ms | 0 / 3 |
| 4 | 7.343 s | 5.661 s | -1681.6 ms | 4 / 0 |
| 5 | 5.395 s | 6.660 s | +1264.8 ms | 0 / 3 |

Median slot difference: +181.0 ms. Largest absolute pair difference: 1681.6 ms.

Both slots use the same installed VM/exporter, guest flags, original source edits and tests. Their Cargo cache directories are independent. All seven guest artifact pairs match, including the deliberately incorrect edit that fails in every mode. Native controls and cold costs remain in the raw report. No timings are discarded.

[Full command report](../paired-identical-tool-corpus-nushell-type-relations-01/summary.md).
