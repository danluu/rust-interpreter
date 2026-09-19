# Strict and cache qualification

All121 expected outcomes pass with isolated tool3e53b127 and the unchanged
adopted exporter/wrapper. Environment, dynamic-dispatch and closure-pointer
fixtures match native execution across interpreter/JIT and cold/warm reuse.
Original, helper-edited and restored Cargo states match native results and
exact artifacts; automatic-cache behavior remains qualified.

Unreachable type and borrow errors prevent guest execution. An actually
partially checked artifact is rejected before scalar execution. Deliberately
invalid handles/memory/signatures keep their original failure behavior.
Source restoration passes. No project latency was measured.

Source aee88c65, supervisor93897/child93900, completes normally. The closure
verifies19 frozen source/evidence bindings and all recorded outputs. Next run
three original candidate profiles against the retained current-host controls.
