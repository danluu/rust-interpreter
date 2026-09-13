# Prepared frontend-worker mechanism screen

This source-only extension has not been tested or benchmarked. The shared publisher now supports its explicit public-build policy, but real
build and 30-command qualification remain pending. The existing strict 27-command
history is unchanged: one original anchor, a wrong production edit, compiled
recovery, five cumulative first-seen edits, and compiled final restoration in
three balanced arms. All 14 original Nushell type-relation tests, manifests,
features, checking, runtime limits, VM options, Cargo jobs4 and suite workers2
remain fixed. The arm settings are explicit frontend workers1/2/1, using the
same actual stock compiler, exporter, wrapper, VM and prepared standard library.
The existing worker policy provides separate workspace namespaces; this harness
does not change any cache implementation or reuse a compiled edited hash.

## Two proofs, without a circular tool key

1. Publish an immutable **public build** through the shared provenance system.
   Its final tool key is the canonical digest of its complete composition,
   including actual binary hashes. A source revision or source-input digest is
   never accepted as that final key. This stage proves build identity and
   workspace correctness; it does not claim worker qualification.
2. Run `experiments/frontend-workers/qualify.py` against that final installed key.
   Its external, typed 30-command receipt binds the exact key, three binaries,
   pinned compiler, unchanged std identity, source inventory and wrapper
   capability. This receipt stays outside the keyed composition because its
   commands and launch reports contain the final key. The screen requires both
   proofs and rechecks the actual command shapes, results, source hashes,
   duplicate-preserving diagnostics, edit/restoration bytecode and process logs.

The updated qualification recipe records
`policy=frontend-workers-qualification-v1`, the source owner, complete crate
inputs and per-child fixture hashes. Old untyped summaries are insufficient.
All eight copied fixture files are bound to the published harness. Every child
guards the six immutable manifest/build-script/proc-macro files as well as the
two controlled edit files; the complete copied source set is checked before and
after each command. The archived consumer binds the qualifier, scripts and
fixture templates to that same published harness. Screen freezing hashes the
exact bytes read by the typed validator and rejects changes before admission.
Its 30 commands are two compiler identity probes, 22 real launcher invocations,
and six direct native diagnostic controls. Source edits3→7→3 affect a shared
dependency used by native build scripts, a proc macro and guest code. Type,
borrow and constant errors, recovery, assembly rejection and restoration remain
required. These controls are separate from the timed Nushell history.

## Shared public-policy extension

Keep the current `qualified-public-toolset-v1` macro policy and its frozen source
and eight-command checks unchanged. The shared module provides this explicit callable interface:

```python
SUPPORTED_QUALIFICATION_POLICIES = {..., 'frontend-workers-public-build-v1'}
validated = validate_public_tool(
    tool_directory, final_tool_key, read_bytes,
    qualification_policy='frontend-workers-public-build-v1',
)
```

The new policy is keyed as `composition['qualification_policy']` and returns
`qualification_scope='public-build-only'`. It reuses the existing pure payload,
binary, public compiler/Cargo, transitive library/platform, dependency/source,
build-profile, complete shared-std, publication and input-guard reconciliation.
It requires an explicitly frozen worker producer source inventory, actual
workspace/build/launcher/screen test receipts and both exporter/wrapper probes; it must not replace the macro's
source01e36c0 or eight-command expectations with permissive alternatives.
Only policy-specific command and capability checks should be dispatched.
No second publisher is proposed here.

The exporter capability must contain the exact `frontend-workers-v1` dict from
`scripts/frontend_workers.py`; the light wrapper must be probed at publication.
`frontend_worker_wrapper` binds the identical capability to the actual wrapper
SHA. The capability envelope still binds the final tool key and exporter SHA.
The shared validator returns the existing composition/capability/correctness,
input_records/searches/platform and payload_paths fields. `validate_live_inputs`
and `validate_input_guard` remain the shared guard APIs. A build receipt may say
published/built; complete worker qualification is supplied only by step2.

`scripts/frontend_worker_screen.public_build` is the callable consumer boundary.
It refuses absent or unsupported typed policy APIs and never falls back to
macro proof. `validate_qualification` is a pure reader-based checker usable by
both live screen admission and the saved assessor. Neither checker invokes a
compiler or trusts a count/status field without its underlying records.

## Timing, audits and archival

Every production launcher, Cargo, compiler and VM operation, normal cache
validity check and required operational setup remains inside the existing
whole-command timer. No time is subtracted. Benchmark-only frozen-input and
installation audits use the same untimed before/after boundary as the existing
strict and macro screens. They do not enable worker execution or replace a
semantic cache check. Their full public input-guard receipts are retained before
and after all 27 commands; original suite/artifact verification is unchanged.

The saved assessor reconciles the same public build, external qualification,
worker receipts, guard records and common std identity using archived bytes.
Text remains exact UTF-8; qualification bytecode is retained as validated
base64 members. It does not need live retired fixture caches to evaluate proof.
Missing receipts, changed sources, a different std/compiler, mixed macro/Cargo/
custom-compiler policies, skipped controls or changed command flags fail closed.

After the shared policy extension, source checks and actual worker qualification
are complete, the intended command is the existing screen with
`--candidate-policy frontend-workers`, identical baseline/candidate tool keys,
one `--std-mir-ready`, `--frontend-worker-qualification <run>/result.json`, and
`--workload-lock /Users/danluu/dev/rust-interp/.work/benchmark.lock` on this host.
This exact existing canonical lock is required; the worker policy never
silently creates a worktree-local substitute.
No custom compiler, Cargo or candidate std argument is allowed. Use the verified
canonical campaign lock for all eventual tests and workloads; setup must not
hold it while a child separately acquires it. This remains one mechanism screen,
not final0.5s qualification, an adoption decision or holdout evaluation.
