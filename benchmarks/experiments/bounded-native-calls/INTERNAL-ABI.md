# Emitter integration notes

## Persistent-register extension (`d664bce`, experimental)

With `--jit-persistent-registers`, a function may assign up to three complete
u128 guest values to x23/x24, x25/x26 and x27/x28. The full-CFG liveness analysis
includes short/interpreted regions, so every VM continuation preserves all of
its possible register inputs. Register arrays remain inaccessible to guests.
Memory forwarding facts still end at each region/call boundary.

An ordinary external entry reserves `16 + 16*N` host bytes, saves x19/LR at
offset 0 and its N assigned pairs from offset 16, then reloads current guest
values from the initialized register array. Internal successors skip that
prologue. A VM continuation spills assigned live values through x0 before
putting the continuation PC in x0, restores the host pairs and x19/LR, and
returns. Budget declines use the same spill rule. Fault exits restore the host
ABI and cannot resume guest code, so they need no guest-register spill.

The standalone native-tree wrapper remains 16 bytes. Its internal entry
reserves `64 + 16*N`, retaining x20/x21 at 0, x22/LR at 16, caller x0/x1 at 32,
profile at 48 and budget scratch at 56. Assigned pairs start at 64. Each native
callee saves/restores only the pairs it changes; unused pairs remain untouched.
The ordinary Call stub keeps its existing 64-byte internal frame and the outer
ordinary frame. It uses the caller's assignment and relies on each child to
preserve those physical values, including on faults. Both frames unwind on a
stub fault. All frames remain 16-byte aligned; x18 and x29 remain untouched.

The original default remains available and analysis limits decline to its
emitter. Assignment counters count published ordinary/tree code instances, not
unique guest functions. Analysis and emission time remain inside compile time.
The [debug qualification](../../../results/persistent-native-04/summary.json)
passes 240 tests, including an expanded assembly probe for x19–x28 and SP/LR.
The optimized check also passes all 240 tests. The
[real E2E result](../../../results/persistent-e2e-01/assessment.md) improves token
23.6% and folded 4.2% paired, but misses the folded target. The ABI checks do not
establish broad compatibility or permit retention by themselves.

The storage, metadata and dedicated emitter described here are implemented in
`linear_memory.rs`, `jit/trees.rs` and `jit/native_calls.rs`. Direct-entry native
checks and opt-in VM integration pass. These checks do
not establish a runtime or end-to-end performance gain.

## State already implemented

`LinearMemory` owns initialized backing bytes plus a private active length.
Deref exposes only the active slice, so existing memory access, allocator budget
and TLS paths keep their live-prefix behavior. `resize` reinitializes the newly
active range, including retained bytes after truncation. `prepare` grows only
backing storage and may decline; `commit_native_len` checks the returned extent.
Five tests cover bounds, zeroing, alignment padding, failed preparation and live
budget accounting. The full workspace passes 212 tests.

`trees::analyze` uses the actual emitter support predicate/local-fill proof and
explicitly allows proposed Call/Return/terminal Trap operations. CFG cycles,
recursive dependencies, unsupported operations and bound overflow decline.
Each static call site contributes its child's full instruction bound. A queue
processes dependencies without recursive host traversal or repeated graph scans.

The memory span includes the function's own frame plus `(maximum direct-child
alignment - 1)` and the maximum child span. All alignments are powers of two;
successive child returns can round the parent's active end no further than its
largest child's alignment. Registers use own slots plus maximum child slots;
depth includes the root callee. Requirements align the current memory end and
check additions to active register/frame counts. Five tests include real VM
instruction/peak-memory comparisons across sibling/nested alignment combinations.

## Dedicated tree emission

Reuse `Assembler::lower`, `checked_address`, branch lowering and local-fill
proofs. Compile every supported region, including short regions and Return.
Keep the 1,024-operation region split to bound local fault relocations. Calls,
returns and traps terminate regions; their successors begin with fresh facts.
Spill live scalar facts and evict cached registers before call setup. A callee
can change caller memory, so no memory forwarding fact crosses a call.

Each tree function has a C-ABI wrapper and an internal entry. Both share the
existing bounded MAP_JIT arena with regular regions. Prepare dependencies before
publishing a parent; a declined dependency makes the complete tree unavailable.
All branches target trusted published metadata. Preserve atomic staging and
typed codegen-limit declines. No code publication or storage growth occurs while
a tree executes.

Suggested internal register contract: keep the ordinary emitter's x0 register
slice, x1 frame base, x2 linear-memory pointer, x3 active linear length, x4 readonly
end, x7/x8 heap pointer/length and x19 cursor. A wrapper adapts the public eight
arguments. Pass a child's guest return destination in x15; internal entry saves
callee-saved registers/LR and moves it into x20. Reserve x21/x22 for call-setup
base/register pointers. Never use the platform-reserved x18.

A 64-byte internal host frame can save x20/x21, x22/LR, the function's x0/x1 and
its profile pointer. Restore x0/x1/profile after an inner call. Keep x3 equal to
the child's aligned base after return, rather than restoring its pre-call value.
The 64-level metadata cap bounds this host nesting; guest recursion stays in the
ordinary VM. Verify x19–x22 and SP/LR with an assembly ABI probe.

Extend the host-only cursor with final active memory length, peak linear length,
root return destination, a table of tree-profile counter pointers and native-call
counts. Preserve the existing remaining-budget/profile-pointer prefix. Use
`repr(C)` and assert offsets. The native path must receive initialized backing
extents large enough for its complete tree, not Vec capacity alone.

Before entry, require all code/storage and the whole-tree budget. Then debit
actual region/Call/Return counts without partial budget exits. On each native
Call, zero the newly active memory range, expose that length, copy arguments in
order, initialize registers according to the existing proof, and enter the child.
On Return, copy its result before truncating to its aligned base. General argument
and return copies need overlap-safe handling; do not assume caller-local sources
or destinations. `checked_address` already accepts a machine register containing
a guest address. Use existing scalar/vector snapshot copies for small sizes and
a custom directional loop for larger ABI copies.

Terminal traps need named native fault identities, distinct from assertions.
Propagate a callee's fault through native epilogues without executing result
copies or further guest operations. Keep codegen/internal errors distinct from
guest faults. An unexpected successful partial return is an internal error.

## Integration order

First implement and differentially test standalone complete tree entries. Then
connect the explicit experimental option to the existing VM Call path: ordinary
root-call argument/depth errors retain their order, and unready/budget/storage
declines use the current interpreter/JIT path. Preparing an already-reserved root
callee requires `base + frame_span` and `register_base + register_slots`; do not
add its own frame/register storage twice.

The VM Call integration still has a host transition for each outer tree root.
Measure root entries separately from generated nested Calls. Follow with native
Call stubs in regular JIT regions if those root transitions prevent the planned
gain; do not count all census-eligible calls as eliminated VM calls.

Profiling needs separate tree block counts/endpoints. Ordinary regions may group
the same PCs differently, so sharing one `jit_block_ends` array would misattribute
instructions. Fresh guest memory/TLS state and existing root/TLS completion remain
owned by the VM. Preserve all benchmark options and measure complete commands
against `b2aa6efe` with the predeclared gates.

## Direct-entry qualification — September 11

The full workspace passes 219 tests (one ignored). The seven native-tree suites
reuse the established call-copy contracts and compare values, instruction counts
and memory peaks with the interpreter. They exercise both profiling modes,
whole-budget pre-entry declines, cold terminal faults, short branch regions,
shared code publication/capacity decline, repeated/nested frame alignment,
initial-zero registers, all ABI copy paths including 513-byte moves, overlapping
return destinations and heap copies. Retained-byte snapshots and canaries check
copy effects beyond the final live prefix. A native assembly probe verifies
x19–x22 and SP/LR for success and fault propagation through up to 64 functions.
[Recorded check](../../../results/bounded-native-emitter-02/summary.json).

## VM integration qualification

`native_execution.rs` connects the option after the ordinary VM Call has copied
arguments and checked root depth/working memory. Conservative full-tree guards
can decline without introducing early guest errors; the original push/dispatch
path remains available. Memory initialization is prepared separately from the
live extent, then the returned cursor is checked and committed. Register backing
is retained while active register accounting returns to the caller.

The default engine loop has a separate specialization without this transition.
Root and TLS completion remain in the VM. Profiles have independent tree block
counts/endpoints; counters distinguish host tree entries from nested native
Calls. Total JIT instruction/entry/byte counters include trees; ordinary JIT
operation/function counters and their tree equivalents are reported separately.
Code-generation time includes tree analysis/preparation, also reported separately.

Six integration suites cover exact instruction boundaries, tight depth/memory
limits, insufficient code capacity, ordinary fallback, cold branches/recursion,
the shared call-copy cases and TLS callback descendants. The C-allocator fixture
exposed a missing heap-presence classification for C allocation opcodes; those
now enable heap addressing in both regular regions and native returns. The first
fixture used an invalid errno pointer and was corrected without weakening the
expected behavior. The failed check remains recorded as `bounded-native-vm-02`;
`bounded-native-vm-03` passes all 225 workspace tests (one ignored). Seven CLI
checks validate the new option and invalid combinations. Release/real workflow
qualification remains separate.

## Ordinary region integration qualification

Source `26833c3` adds an ordinary 16-byte wrapper around the 64-byte Call-setup
frame and links successful stubs back to ordinary internal entries. Its cursor
is now 80 bytes: the existing prefix and fields through generated-Call count at
offset 48, descendant instruction count at 56, readiness at 64 and successful
stub count at 72. Raw cursor pointers originate from the complete allocation.
Default ordinary entries keep their smaller cursor and cannot reach stubs.

All 231 workspace tests pass in debug/release, including mixed ABI declines and
faults, linked loops, heap growth and VM-retained alignment padding. The saved
real workloads execute the stubs and pass original assertions. See
[the implementation notes](REGION-CALLS-NEXT.md) for readiness-cache and
accounting contracts; complete-command performance qualification is separate.
