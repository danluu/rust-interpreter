# Qualify the resumable-to-tree bridge in stages

Follow [the bridge contract](../bounded-tree-bridge-census/BRIDGE-CONTRACT.md).
The broad eligibility census justifies a prototype, not adoption. The first
stage contains only admission and fault-frame materialization primitives; no
runtime option or guest execution path invokes them yet.

Run the independent wide-integer admission model and native ABI/descriptor probe
in debug and release. The probe writes only owned initialized host descriptors,
checks untouched neighbors and guest backing, and verifies x19-x28, LR/SP and
the first-fault capture across simulated unwind depths. Keep the adopted paths
unmodified until these primitives are qualified. A later wiring change needs
complete nested/fault/limit fixtures and all broader workspace and real-edit
qualification described in the contract.

Use the existing shared target with two Cargo workers, 45-second shared-lock
admission, 16 GiB initial free disk and 8 GiB per child. Freeze exact sources and
retain all command results and setup times. No benchmark, subagent or AWS action
is part of this focused primitive qualification.

The next stage enables the extended tree ABI only in focused native fixtures.
A shared region partition excludes any function with a guarded ordinary body,
then propagates exclusion to all ancestors. No VM runtime option enables it.
Run four controls per profile, including the previous primitives, nested
success/fault materialization and transitive guarded-body exclusion. Nested
fixtures cover both profiling modes and persistent-register modes, failed
arguments, faults after completed children, arithmetic, assertion, trap and
memory failures, with independently specified active descriptors and ABI checks.
