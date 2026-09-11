# Lightweight compiler routing experiment

The one-cycle Nushell diagnostic rebuilt 19 units after a real generic API edit.
Its warm time is mostly actual checking and build propagation. A separate
30-triple version-probe diagnostic found roughly 9.7 ms additional overhead
when the heavy exporter delegates ordinary rustc. Cold graphs contain hundreds
of compiler units. This motivates a bounded routing change, not a prediction
that all observed unit time is removable.

Add a std-only wrapper in the exporter package. Move the existing Cargo routing
rules into a shared std-only module. For unselected units, exec real rustc with
the existing argument transformation. For selected exports, exec the adjacent
installed exporter with the original argv, allowing that same router to apply
the transformation once. Keep ordinary standalone exports and historical
two-binary installed tools usable. New immutable manifests include and verify
the third executable; do not select an unmanifested file merely because it exists.

Preserve package/crate/manifest selection, primary-package distinction, test and
harness=false expansion, explicit target and sysroot checks, host tools, ordered
rustflags, always-encode-MIR policy, jobserver descriptors, environment/cwd and
Unix exit behavior. No checking is deferred or removed. A Cargo failure or
selection change must never execute an old sidecar. Unsupported wrapper forms
are not silently granted new semantics as part of this change.

Qualification:

1. Check routing matrices for actual Cargo forms, wrong packages/manifests,
   test variants, host/guest sysroots, conflicts and ordered argument forwarding.
   Run debug/release workspace checks and verify the new wrapper's dylib list
   does not load rustc_driver. Check actual delegated and selected subprocesses,
   errors, cwd/environment/jobserver descriptors, and installed-manifest errors.
2. Run the existing launcher source/feature/flag/selection/revert and dependency
   checks with original assertions, plus explicit old-tool compatibility.
   Qualify real std-MIR host/target builds using the pinned Nushell interface case.
3. Compare the new tool against fixed 78e60cdd using the same ordinary JIT flags
   in both modes (resumable/persistent calls off in both). The VM should be
   byte-identical; require matching exported artifacts within every pair. Keep
   native controls and original tests/wrong edits/check references unchanged.
4. After one-cycle pgrust/Nushell qualifications, repeat actual interface edits
   with balanced mode order. Measure target-cache-cold builds separately, with
   fresh histories and explicit setup exclusions. Extend to Ruff, private rg-aot
   aggregates and fre before generalizing. No full-suite claim follows.

Retain the routing change only with intact semantics and controls, a material
end-to-end improvement (predeclared target: at least 5% median cold-command
reduction on the large Nushell workload), and no unresolved paired warm-command
regression greater than 5% on the checked workloads. Version-probe deltas alone
cannot pass this criterion. Do not pool costs across projects or filter samples
for host load. Native-call performance gates remain failed and separate; this
experiment does not change them or the runtime defaults.

Status: shared router, std-only binary, manifest/launcher integration and eleven
routing tests implemented. `lightweight-wrapper-debug-01` passes all 268 workspace
tests, one ignored, with unchanged archived sources. Release/build publication,
subprocess/launcher qualification and real-project comparisons remain pending.
