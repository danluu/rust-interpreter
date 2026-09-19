# Read actual remaining costs after the full scheduler guard closes

Bind the complete110-command history and verdict, all relevant source/record/report
hashes, and full session CPU accounting. Read15valideditedreports per custommode
(60total), without running a guest or compiler. Report build-to-ready, execution,
request, outside-worker, preparation and emission intervals in their actual scopes.
Also retain observed longest-test duration and preceding test work in each session
report; exact114index/name coverage and finite durations are required. Do not assert
that ordering helps. Accept the completed history regardless of its timing verdict.

Overlapping worker/compilation sums are not CPU or additive stage partitions.
These saved intervals select future work; they cannot change the completed gate
or authorize an unchanged retry. Sharedlock45s,12GiBadmission,8GiBclosure.
