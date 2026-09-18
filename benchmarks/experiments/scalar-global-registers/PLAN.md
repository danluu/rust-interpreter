# Qualify a bounded cross-block scalar register allocation model

Persistent native caching remains deferred after exact real-edit body and literal
churn censuses. A separate custom-backend opportunity is retaining scalar values
across basic blocks. The current scalar allocator always spills such values.
The earlier scalar-register-pressure-03 census used a parked store-log prototype;
its counts are a hypothesis source, not a current adopted-runtime measurement.

First implement only a test model. Build narrow live-computation liveness across
the full scalar CFG, including predecessor-specific inputs consumed by spilled
phis. Construct an interference graph and use the existing four registers
x3/x15/x16/x17. Phis, inputs, constants, base addresses, wide values and all other
ABI registers keep their current treatment. Read all inputs before assigning a
definition. Rank by static use/definition weight relative to graph degree and
select the global result only if its static weight improves on current allocation.
Decline on bounded shape/work failure; do not expand the register bank.

Bounds: 4,096 candidates, 512 blocks/bytecode PCs, 16,384 IR nodes, 250,000 events,
8 million charged liveness/interference operations, plus bounded graph coloring.
The maximum adjacency bitmap is 2 MiB; no executable code is produced.

Qualify split live ranges, diamond paths, narrow widths, stack phis, forced
clobber detection, dead nodes and bounded declines. An independent forward path
simulator checks the actual last-written node in each allocated physical register,
without using the allocator's backward liveness/interference sets. Run controls
in debug and release before the release-only saved-body census.

Reconstruct every scalar body from the three closed scratch-memory-values-profile
adopted captures byte for byte. Apply the model to those exact plans and use only
their successful scalar PC counts to report remaining spill definitions/operands.
Keep baseline/global statistics, all declines and negative changes. These counts
exclude phi-edge transfers and private failures and cannot predict a speedup.
No runtime flag or native emitter integration is part of this stage.

Use the ROOT shared target, two Cargo workers, shared lock and 8 GiB child floor;
build admission remains max(14 GiB, 8 GiB + twice allocated target). Freeze all
sources, inputs and outputs and close successful or failed commands. A later
runtime candidate would need emitted-code/ABI/value/fault/budget qualification,
original real-guest comparisons and a preregistered changed-source primary.
