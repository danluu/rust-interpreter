# Explicit large-literal parameters for trusted template reuse

Motivation: actual checked parser edit trace, 2563immediate-only body misses with
152.106ms summed emission; the safely unmodified store-only emitter subset covers
just154misses/5.166ms. Do not implement that narrow subset or weaken ordinary
constant-folded identity. Instead prototype a distinct literal-parameter mode.

Select Op::Imm whose low64bits are at least65536; preserve small constants for
folding. Exclude definitions participating in the current fused local-fill plan.
The threshold is a performance policy, never a claim that a value is a pointer.
Bind the selected PC set and each half's MOVZ/MOVK width pattern in a new key domain,
plus all other caller fields, IDs, callee layouts/zeroing/scalar inputs and options.
The normal v3 key and emitter remain available without this explicit feature.

The emitter represents each selected definition as an opaque Literal{pc,value}
fact. Only materialization consumes its current bits and records a relocation
with exact PC, half, destination register, word range and old encoded value.
Other folds/constant branch selection treat it as unknown. Local-memory forwarding
must preserve opaque behavior rather than synthesize constant facts. Range-group
analysis and call-slot hints must mark the same definitions opaque; liveness and
register assignment depend on operand/control structure only. Fused-fill literals
stay exact-key inputs. Audit every Fact match and every whole-function analysis.

Retain trusted in-process templates only; fresh code arenas/current guest owners.
Capture a complete literal-site manifest through the sole materialization path,
validate ordered/disjoint sites and old encodings, and require matching selected
current Imm PCs/shape before patching. Missing, duplicate, changed-PC/half/register,
wrong-width and stale/corrupted records must decline. No external native cache.
Keep all existing assertion/scalar relocation and arena/resource checks.

Qualification before timing: focused key/ledger controls in both profiles; live
old/new literal cases versus the interpreter including folds, branches, loads,
aliased memory, pointer faults, call slots, arithmetic extremes and exact budgets;
full Rust workspace/Python/strict launcher controls as source changes require;
actual parser suites with fresh emission checked on every hit. Compare observer
phase/hit changes, then choose a new changed-source E2Eprimary only if useful.
Disabling folds can worsen execution: count the whole command and preserve original
A/A, CPU and project guards. No adoption from hit rates or diagnostic intervals.

Two workers; benchmark.lock45s; dedicatedbuildtarget neverclean; existingbuild,
replay/parser/Nushell admission floors; no goals/subagents/peerprocess changes.
The digest full guard stays unmeasurable, buffered keys and narrow relocation stay
parked, and the adopted runtime remains the control.

Focused01:27template controls passed; two new reference comparisons rejected
JIT-only options passed to Engine::Interpreter. Preserve failedrecord. Focused02
clears only the reference engine options, keeping memory/instruction/frame limits
identical; no runtime implementation change follows from that fixture error.
