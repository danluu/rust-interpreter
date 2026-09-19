# Parameterize selected literals before reusing generated code

The prototype makes selected literal values explicit relocation inputs. Ordinary
constant-folded code cannot safely ignore these values in its cache key: they can
change arithmetic, branches, memory facts, range guards and call-slot hints. The
experimental emitter therefore treats selected literals as opaque and records
every emitted occurrence in both a typed relocation list and an independent
site manifest. Restoration checks those records and writes the current values.
The key retains the native MOVZ/MOVK width pattern and all other function and
callee inputs. The current heuristic selects low64 values at least65536, excluding
fused-fill values; this threshold is not a claim that those values are pointers.

This follows actual parser miss evidence:2563missed bodies changed only immediate
values, carrying152.106ms of summed diagnostic emission across five valid edits.
A narrower, optimization-preserving subset covered only154misses/5.166ms and was
parked. These intervals overlap across workers and are not projected wall savings.
[Miss evidence](TEMPLATE-MISS-HISTORY-20260919.md).

The focused proof passes34controls in each profile and24with parameterization off.
It includes fresh/restored native word and metadata equality; independent manifest
loss/reassociation rejection; current addresses and exact engine fault contracts;
memory forwarding and switches; instruction-budget boundaries; and40native
arithmetic/overflow combinations compared with fresh JIT and interpreter results.
[Focused proof](../results/parameterized-literals-focused-05/summary.json).

Earlier focused attempts are preserved. Two test fixtures incorrectly demanded
that the reference interpreter accept JIT-only options or use the JIT's memory
fault wording. Another fixture exceeded the existing range planner's4096-byte
bound; its corrected large-literal subtraction yields a valid8-byte offset.
One focused and one workspace attempt timed out before admission to the shared
benchmark lock, starting no build or test. None of these establishes a runtime
correctness failure, and none is reported as a successful performance experiment.

Next gates are full workspace qualification,1824saved parser invocations with
fresh re-emission of every cache hit, and separate phase attribution. The change
can reduce compilation while making execution slower by losing constant folds;
key construction, manifests and restoration also cost time and retained memory.
Only a newly qualified, changed-source end-to-end comparison can justify adoption.
Strict Rust checking remains required, the default runtime is unchanged, and
this is not yet evidence that the design improves development of large projects.
