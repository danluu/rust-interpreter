# Conditional integration of the measured memory-operand stack

The [completed comparison](../results/memory-operands-complete-01/assessment.md)
fails the pgrust CPU guard. This integration remains conditional and has not
been executed. The next work is a distinct composition with compiler-identity
lookup caching; it must earn its own completed result. The source review below
records the scope of the original memory-only proposal.

Token and folded pass their prospective gates. Pgrust fails its CPU margin,
so the original memory-only proposal cannot advance. The separate
[memory/lookup composition](../benchmarks/experiments/memory-lookup/WORKFLOW.md)
must complete all five cases before an integration decision; its frozen
benchmark inputs stay unchanged meanwhile.

The measured runtime is source8d719f4, toolf0af2e3e, retaining exporter/wrapper
80a9020f/cff204c5 from the qualified wide toolf8713aaa. Its final emitter and
register allocation exclude the failed paired-register and guarded-indirect
additions. Its source includes the corrected frame-clear proof, whole-call
expansion, budget/call-slot protocol, wide bitwise operations and the new
memory operands. The full stack is compared directly with the fixed anchor;
historical component ratios are not multiplied or relabeled as passes.

Read-only integration review against main93d8de8 finds28 changed Rust/package
files, predominantly tests, plus a small launcher delta. Exporter sources and
the bytecode transformations it invokes are unchanged from the qualified
compiler/runtime integration at241ac6e. The runtime library has changed since
that exporter was built, so a normal complete-tool rebuild still needs actual
export and execution qualification.

The original memory-only import scope was:

1. Branch from current main in the original root worktree after the controller
   is terminal. Preserve the completed experiment branch and all raw evidence.
   Import the exact qualified Rust/package files and necessary function-cache
   launcher support. Keep main's fresh compiler lookup path. Do not blindly
   merge the experiment's unrelated optional toolchain-lookup cache or its
   standard-MIR helper changes.
2. Build all tools from that integrated source, with428 debug/release checks,
   two Cargo workers, the shared lock and current disk admission. Verify the
   precise Rust inputs against the qualified source. Preserve the distinct
   new build/tool identity; do not label it the old measured executable.
3. Qualify strict real Cargo edits, unreachable type/borrow errors, cache
   invalidation, native/reference agreement, exact saved selections and suites.
   Compare newly exported real artifacts and current per-PC profiles with the
   retained tools. Unexpected differences require explanation before merging.
   This is integration verification, not a retiming of the completed candidate.
4. Merge the verified implementation and concrete usage documentation to main,
   with the completed comparisons and native disadvantage visible. Keep
   unsupported libtest/unwind/thread semantics explicit and runtime options
   consistent with their existing contracts. Continue from that verified base.

This scope is retained for the review record, not queued for execution. The
current composition intentionally includes the optional compiler-identity
cache, so any future integration needs a new source manifest and review that
include `scripts/toolchain_lookup.py`, its CLI and standard-MIR wiring, and
its invalidation tests. The composition already passes 138 harness tests and
20 real Cargo checks with the measured VM; those do not replace qualification
of a rebuilt integrated tool. Its fresh-lookup control remains available.

All five prospective performance gates must pass before that integration.
Preserve any failure without changing a completed rule or repeating the same
timing trial to seek acceptance. A later candidate needs a distinct
implementation and a new prospective comparison.
