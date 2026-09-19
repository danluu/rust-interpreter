# Implicit-zero register storage: candidate contract

Status: the closed narrow-register-storage census admits a bounded prototype.
No production representation or emitted code has changed yet. This is a distinct
proposal from packed native-register allocation and paired virtual-register
spills, whose failed comparisons remain closed.

A validated function can prove that every definition of a particular logical
128-bit register clears its upper64bits. The existing bounded
`register_widths::prove` includes unreachable definitions and declines unknown
or wide definitions. This establishes a logical value, not physical backing:
`needs_initial_zeroes` already allows reused frames to retain old bytes when
all reads follow writes. The old upper words can therefore be nonzero.

The candidate would give such registers an implicit zero upper word during
resumable execution. Keep all existing allocation, initialization, frame,
working-memory, checking, budget, fault and profiling rules. Preserve low words
and the original16-byte private register slots. Do not introduce a new guest
address representation or change any addressable guest memory.

The complete read contract is:

- Native ordinary regions and Call/Return transitions synthesize zero for high
  reads of classified registers. Persistent-pair reloads must do the same;
  changing only `Assembler::get` misses these direct loads.
- `raw_spill` may omit classified high stores only when that read contract is
  enabled for the function. Persistent assignments and temporary arithmetic can
  initially retain their current full-width behavior.
- Before interpreting an instruction in a function with this representation,
  normalize its classified register read operands in place. Visit every read
  role before executing any writes, including aliases, indirect handles, TLS,
  descriptors and uncommon fallbacks. The exhaustive shared operand visitor
  is preferable to duplicating a partial opcode list. A later selective repair
  proof could remove already-masked consumers, but is outside this first trial.
- Publish the proof metadata only with successful native publication. Declined,
  cold, unsupported and non-resumable functions keep the existing representation.
  The active function after a native Call/Return chain owns the repair metadata;
  a previously active caller cannot supply it.
- Both the actual native emitter and diagnostic re-emission use the same proof.
  All native exits and returns preserve the C ABI. Scalar leaves keep their
  separate private representation and transaction rules.

Bound proof work and retained metadata. Include the proof and repair costs in
complete changed-source commands. Counts of omitted stores and sampled PCs are
only a reason to test the idea, never an end-to-end gain. Before implementation,
compare the census's exact high-load/store coverage with interpreted operand
counts, and audit every direct register-backing access.

Focused qualification must include reused storage deliberately poisoned in its
upper words; wide and narrow functions sharing a stack range; full-width reads
of narrow logical values; aliased reads/outputs; skipped definitions requiring
initial zeroes; persistent reloads; native-to-interpreter-to-native transitions;
all instruction-budget prefixes; faults, indirect validation and TLS callbacks;
and code/proof-bound declines. Compare results, errors, memory and original-PC
profiles with the adopted implementation. Native host registers/SP must remain
preserved. Physical dead backing bytes are not a substitute for logical-value
checks.

Only after focused and full contracts pass should the existing40-command
changed-source token primary run. Retain its original wall/CPU/A/A gates; full
five-project and both parser histories are still required before adoption.
Main stays on the adopted runtime until that complete qualification passes.
