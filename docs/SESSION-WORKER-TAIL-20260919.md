# The parser's longest test starts at the end of the queue

The complete saved census covers 10 valid history-on/off reports and 1,140 test
intervals from literal primary05. The longest test is last on its worker in all
ten reports. With history enabled, its median duration is203.713 ms after41.111 ms
of earlier test work on that worker; the peer worker has41.556 ms of total test
work. The preceding-work range is37.490–62.691 ms. With history disabled, preceding
work has median79.316 ms and the longest test223.240 ms.
[Audited intervals](../results/session-worker-tail-census-01/summary.json).

These are actual ordered elapsed intervals, not a predicted scheduling speedup.
Reordering changes compilation, cache warmth, worker assignment and contention;
prior-test sums exclude worker setup and loop/report overhead. The original
40-command primary still fails its wall gate, and is not repeated unchanged.

A general next experiment can learn bounded advisory test durations from the
previous completed request and start slow entries earlier. It must execute every
current entry exactly once, preserve original indices and canonical report order,
create fresh guest state, keep current environment and limits, and use no cached
outcome or benchmark-name exception. Missing or unusable hints must fall back to
ordinary catalog order. Shared function-key hashing remains disabled because its
aggregate preparation result did not justify another primary.
