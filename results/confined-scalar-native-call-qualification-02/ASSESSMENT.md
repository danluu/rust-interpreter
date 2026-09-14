# Strict scalar Call compatibility qualification

All 121 commands passed their expected outcomes, including twelve intentional
negative commands. Fully checked environment, dynamic and closure-pointer
fixtures match native/interpreter/JIT execution with cache off, cold reuse and
warm reuse. Strict Cargo helper edits change the result, restored sources restore
it, and unreachable type/borrow errors stop before VM launch. An artifact from
the actual demand frontend carries the partial bit and scalar mode rejects it.

The build's 590 tests/profile and production VM remain unchanged. Its 468 frozen
inputs are closed. Qualification source hashes bind to `a6c75d15` and the earlier
checkout revision: a failed closure command was followed by the run launcher
before the pending source commit completed. The closure verifies every frozen
source hash against the retained Git versions and every log/terminal hash;
the raw plan's checkout revision alone is not the complete harness identity.
Future qualification admission requires a clean tracked working tree. This
bookkeeping correction changes neither guest source nor the installed VM.

This is correctness evidence. Original project profiles and end-to-end edited
source timing are still required before adoption.
