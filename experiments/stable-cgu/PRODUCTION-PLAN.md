# Separate production compiler qualification

Status: source-only plan; no production configuration has been activated and no production build has started. First finish the current assertions-enabled package, interpreter qualification and same-binary stable-CGU off/on mechanism screen. Coordinate any later production build after those measurements and normal disk/lock admission.

The current compiler is optimized but has compiler, tool and native-standard-library debug assertions and overflow checks enabled. In the pinned compiler, `compiler/rustc_interface/src/passes.rs:1090` adds HIR validation under compiler `cfg(debug_assertions)`. `bootstrap.example.toml:647-686` documents inheritance of the standard-library settings. Consequently, the current package is useful for correctness and a same-binary mechanism comparison; it is not the intended final production compiler profile for the absolute build-time target.

Use a new owned source worktree, proposed `/Users/danluu/dev/rustc-stable-cgu-production-20260913`, at the exact frozen patch commit `73a11f167216d3955c277ed47f9b8cc68208105b`, with a separate build directory and separately recorded bootstrap configuration. Keep optimize=true, debug info level 1, thin-local LTO, 16 compiler CGUs, the same target, stage0, exact CI LLVM, source patch, two build jobs, disabled compiler incremental compilation, and real source-commit reporting. The original proposed build-profile changes remain:

```toml
[rust]
debug-assertions = false
debug-assertions-tools = false
overflow-checks = false
debug-assertions-std = false
overflow-checks-std = false
```

The subsequent strict integration found a separate distribution defect: the assertions-enabled configuration omitted `remap-debuginfo`, and its native std metadata contains relative source names with missing diagnostic snippets. Prepared std MIR has the same relative-name problem and its overridden sysroot has no rust-src tree. Add `remap-debuginfo = true` to the **new** production configuration and implement the separately versioned prepared-std source-path policy in [SOURCE-PATHS-PLAN.md](SOURCE-PATHS-PLAN.md). The complete proposed configuration is [bootstrap-production-source-paths.toml](bootstrap-production-source-paths.toml); it has not been activated. The original [bootstrap.toml](bootstrap.toml), frozen compiler, package06 and all earlier receipts stay unchanged.

This source-path amendment also changes compiler/native-std build inputs; qualify it as a distribution repair alongside the production profile. A fully repaired compiler must produce its own complete snippets. The preliminary `verified-std-source` comparison, including its source-derived snippets, cannot satisfy this production gate. Literal absolute filenames differ across independent installations; the source-path plan uses an explicit, equal, diagnostic-only compiler remap during correctness qualification and leaves the strict comparator intact. No such qualification-only mapping enters performance samples.

The native std policy is explicitly assertions/overflow off in this separate production package. This changes both compiler implementation code and its native std, so any qualification-to-production difference must be reported as a profile change, never credited to stable CGU grouping. Normal downstream Cargo profile flags, user-code debug/overflow checks, strict compiler analyses, proc-macro execution, build-script execution, artifact validation, and real source edits stay unchanged. The production package gets a new artifact/provenance identity even though its source commit is the same. Its compiler-private libraries, native std, runtime, exporter tools and VM bindings must be qualified together; none may be copied from the assertions-enabled package by presumed compatibility.

Preparation may reuse a separately copied and digest-verified owned CI LLVM archive. Do not build LLVM from source, use peer caches, change the current compiler, or retire current evidence. Plan an initial 28GiB build/package/test budget plus the 8GiB free-space floor, then refine the estimate using retained source/build inventories before admission. If sufficient free space is unavailable, report that and coordinate task-owned evidence-preserving retirement separately. The shared canonical lock and at most two jobs remain mandatory; an observable supervisor may queue for at most 600 seconds. No production workload is authorized to overlap the current measured screen.

Run the same stage2 build, tracked-option test, partitioning directory and run-make history, std/dev component production, complete runtime-file equality checks, native binary control histories, immutable installation, and full interpreter integration. Preserve every new attempt and exact compiler/config/source/log/artifact hash. Finally compare stable CGU off versus on within this one production compiler and matching complete histories. Count full edited build-to-validated-artifact latency. Never compare qualification/off against production/on or use setup timings as warm-build results.

The next proposed implementation combines that profile and source-path repair with the separately reviewed per-MonoItem patch. Exact ownership, dependency, capacity, stage, packaging and strict qualification gates are in [MONO-PRODUCTION-ADMISSION.md](MONO-PRODUCTION-ADMISSION.md). This supersedes the earlier single-policy checkout proposal for the next experiment; it does not activate a configuration or alter the frozen qualification build.
