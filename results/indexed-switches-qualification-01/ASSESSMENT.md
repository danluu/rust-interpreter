All 122 strict/cache qualification commands pass their expected outcomes.
Original environment/dynamic/closure fixtures agree with native execution under
interpreter, ordinary JIT and resumable/scalar JIT with indexed switches enabled.
Cold/reused artifacts match. Real helper edits change results; unused type and
borrow errors reject execution, including automatic-cache/no-incremental paths.
Actual partial artifacts reject indexed switches and scalar Calls separately.

Source restoration and terminal/source bindings are verified. These commands
qualify correctness and strict checking; their duration is not an end-to-end
performance result. Original workload replays and changed-source gates remain.
