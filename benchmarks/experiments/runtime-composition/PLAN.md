# Qualify one prospective runtime composition

Start from adopted scalar/scratch runtime df4006e0 and the exact diagnostic tree.
Compose these previously qualified mechanisms, retaining all their failed gates:

* Native indirect transitions: delta a80fb30e..9d54d4c7, including complete-memory
  fault controls, exact signature/layout and full-width target validation.
* Checked readonly scalar leaves: delta 6761f5e8^..a97c5234. Keep original read
  order, full range checks and private failure/ordinary replay. Heap-free entries
  never consult uninitialized heap registers. External writes remain excluded.
* Successor-only spilling: runtime delta 0cd5b296. Branch operands remain in their
  live facts until exit consumes them; tree-call tails retain the prior rule.

Retain current main c620a19d's compiler-selection fixes in the launcher and its
new tests. Compiler/exporter/wrapper binaries remain exactly the adopted df4006e0
versions for matched comparisons. No aggregate output expansion, narrower range
threshold, new capture cache, guest-checking relaxation or native backend fallback.
The two new interaction controls route readonly scalar children through indirect
calls after dead branch operands, comparing complete linear/heap memory with the
interpreter on success, ordered faults, every budget and resource/code tails.

First run the complete workspace in debug and release, full Python discovery,
and release VM build under the global lock. Require all commands to pass, equal
workspace counts across profiles (at least631), all named interaction/component
controls, at least431 Python tests with exactly22 declared skips, including the
new compiler-selection controls. Record actual counts; do not claim old tests as
fresh runs. Install an immutable composed tool only after success. Two Cargo/test
workers, sole shared ROOT target, admission max(14GiB,8GiB+twice allocated target),
8GiB child floor; source remains frozen throughout each run.

After closure, run strict/cache/native-reference workflows and exact original-PC
profiles against the adopted controls. Only then run one fresh40-command full-
token primary with five genuine edits, wrong/restored controls, baseline/duplicate/
candidate/historical anchor/ordinary native, normal entropy and two workers.
Keep the original gate: median wall ratio <1 minus maximum individual absolute
wall A/A deviation; CPU ratio <=1 and ratio plus CPU A/A <=1.05. Do not sum prior
stage observations or retry an unchanged failure. A pass only admits the full
five-project histories and both parser guards; it is not adoption.
