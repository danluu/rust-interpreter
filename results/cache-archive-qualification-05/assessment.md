# Archive coordinator after adding check/custom target selection

The unchanged archive fixture suite passes all 40 rejection checks and four
coordinator scenarios against the new CLI integration. Successful retirement,
partial write failure, verification failure and recovery after 1,000 retired
fixture paths retain their previous behavior. File bytes, modes, timestamps,
hardlinks and the two macOS root attributes restore correctly; the preserved
older-format archive also restores.

The [summary](summary.json) binds the exact coordinator and cache-selection
sources. Supervisor 9782 and worker 9788 finished with status 0. Separate
[selection qualification](../workflow-cache-evidence-01/assessment.md) checks
31 refusals and nine actual completed check/custom targets. Neither
qualification modifies real compiler caches.
