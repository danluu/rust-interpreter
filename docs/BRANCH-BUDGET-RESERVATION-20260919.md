# Branch budget reservations: qualified experimental implementation

The default-off `branch-budget-reservation` feature implements the next custom
AArch64 JIT candidate. It has passed the focused and workspace correctness
checks below. No changed-source timing has run, and the adopted runtime remains
unchanged. This is a reservation mechanism; the earlier guard-only credit draft
in `REGION-BUDGET-CREDIT-DESIGN-20260919.md` remains parked.

The current runtime already charges ordinary native regions once each. This
candidate reserves enough instructions for a bounded forward path when entering
a region. A certified successor enters after the budget debit; a shorter path
refunds the excess. Calls, backedges, unsupported instructions and destinations
with range checks end the reservation. Every external entry still checks and
debits its own reservation. Credits are capped at 4096 instructions.

Range plans are computed exactly once in their original order. Edge refunds use
non-flag-setting ADD on the existing budget register, x22. Fault, assertion and
interpreter-transition tails refund unused successor credit. A budget or range
check decline occurs before reservation and refunds nothing. A missing certified
native target rejects unpublished code rather than executing an unsafe fallback.

The saved native-PC samples motivated this work, but sample locations do not
measure instruction latency or establish a dependency stall. More generated
branches and refund code, planner work, and earlier fallback at short budgets
could offset the saved checks. The complete edit/build/test command decides
whether the mechanism helps.

Independently closed qualification:

| Stage | Result |
| --- | --- |
| [Typed planner](../results/branch-budget-typed-planner-01/summary.json) | Six controls each in debug and release: unequal paths, cuts, caps, discovery and range-plan ordering. |
| [Native controls](../results/branch-budget-native-focused-01/summary.json) | Eight controls each in debug and release: short budgets and external entries, fault state, ABI, guard decline, code maps, unpublished capacity refusal, splits and flag independence. |
| [Native-map observer](../results/branch-budget-native-observer-01/summary.json) | Nine Python controls. The new reader validates positive-refund thunks and their credit arithmetic; it does not claim independent certification of every zero-refund link. |
| [Workspace prefix](../results/branch-budget-native-workspace-01/assessment.md) | 446 Python tests passed, 22 skipped; 622 Rust tests passed, 13 ignored in each build mode. Disk admission stopped the controller before its fourth command. |
| [Workspace continuation](../results/branch-budget-native-workspace-02/assessment.md) | Revalidated the unchanged passing prefix and ran only the missing release VM build. No completed test was repeated. |

The feature-enabled VM is
`887b8b138519f79abff80c9ea61477c7cb1a6f708e79efb14e8e89a05af53849`.
The implementation and complete source history are retained on
`experiment/branch-budget-reservation-20260919`; the native implementation was
registered at `532d5d52` before its focused tests.

Three original fre semantic profiles subsequently completed successfully with
exact logical per-PC counts, peak memory, entropy use and generated-code maps.
Their [independent closure](../results/branch-budget-native-profile-01/closure.json)
recomputed all three comparisons. Two earlier closure admissions timed out
before checking evidence; neither reran a guest. The [experimental installation](../results/branch-budget-native-install-01/summary.json)
then composed that exact VM with the unchanged adopted compiler and wrapper.
Its tool key is `2ce1d2e2fd210103b2eceb47754774f4f19094d544b452e62b9d5c5be255f3d1`;
installation and readback both completed successfully without a default change.

Next, qualify the primary controller and run the fixed 40-command source-edit
history. Only its five valid edits enter
the timing gate; original, wrong and restored-source controls stay visible.
The wall ratio plus A/A allowance must be below one, with the existing CPU
ceilings also satisfied. A pass admits the full public, private rg-aot, parser
and Nushell guards. A failed gate parks this candidate without an unchanged
retry or threshold adjustment. Strict Rust type and borrow checking precede
guest execution throughout.
