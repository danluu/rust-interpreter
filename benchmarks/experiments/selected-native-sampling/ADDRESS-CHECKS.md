# Branch on the guest memory arena before checking the range

The exact source-bound native decoder attributes 22.47% of block-test samples
and 15.86% of exhaustive-test samples to heap-aware static-size address checks.
Tag translation alone accounts for 16.24% and 11.61%. These partial captures
justify a runtime experiment; they do not predict its speedup. The earlier
native-memory-parts experiment removed unused load/store halves and remains
parked. This experiment changes the pointer-translation control flow instead.

On the resumable JIT path, branch once on the existing unsigned heap-tag
comparison. Linear accesses then use linear base/length/readonly registers;
heap accesses subtract the tag and use heap base/length. Preserve zero-size
behavior, null rejection, range and size checks, write protection, fault order,
scratch-register contracts and exact logical budgets. Never infer an arena from
only bit62: malformed values with bit63 set still need the old unsigned range
semantics. Keep ordinary regions and old call modes unchanged. Bytecode,
exporter, rustc checking and all guest programs remain unchanged.

Add an independent matrix comparing generated accesses with Memory operations
across read/write widths, null and tag boundaries, heap/linear ends, readonly
prefixes, large invalid values and zero-sized accesses. Exercise a full copied
range, aliased registers and exact-budget fault ordering. All existing tests
must pass in debug and release before runtime measurements.

Host qualification floor: 4 GiB. Reuse the existing populated host cache,
two workers and locked offline dependencies. If needed, transparently compress
only explicitly verified completed diagnostic evidence; preserve paths, exact
logical bytes and metadata. Keep the 4 GiB host admission and actual-project
storage floors unchanged.

After correctness, run six alternating baseline/candidate runtime pairs on the
original current token suite, folded suite and pgrust suite, with two already
recorded entropy streams per suite. Require exact output, instructions, memory
peaks and full entropy consumption. The baseline is the qualified main selector
VM (tool8a169a01). Require at least10% median paired token wall improvement,
improving CPU and no greater than5% median wall/CPU regression in either guard.
Failure parks this candidate without retiming. This saved-artifact screen is
conditional on recorded inputs and is not an edited-command result.

Only a passing screen permits a real source-edit/build/test comparison using
matched native and retained-engine controls, original assertions, deliberate
wrong edits and restored-source checks. Keep exporter/tool cache compatibility
explicit. Main receives runtime changes only after those gates pass.
