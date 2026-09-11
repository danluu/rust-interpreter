# Continue after three fixed cold histories

All three cold histories and both fifteen-cycle warm primaries reverify. The
third cold command reduces wall time 48.26% and raises child CPU 30.04%.
Neither exact failure bound exceeds its threshold with three observations
remaining: minimum possible six-sample median ratios are 0.2455673765 wall and
0.6222435835 CPU. These are bounds, not missing measurements or final estimates.

Continue the fourth prescribed history in native, candidate, baseline order.
The primary protocol remains incomplete, with unchanged wall/CPU thresholds
and no early acceptance or held-out eligibility. Supervisor 15552/controller
15563 finished successfully. See [decision](summary.json) and
[third history](../worker-count-nushell-cold-03/assessment.md).
