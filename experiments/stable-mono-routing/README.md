# Explicit per-MonoItem compiler routing

Status: source-only implementation. Python syntax and whitespace were checked;
no compiler, build, test, standard-library preparation or benchmark was run.
The per-MonoItem compiler patch remains a separate unbuilt experiment. No
performance, runtime-correctness or 0.5-second claim is made here.

`--stable-mono-cgu-partitioning off|on` is an explicit selector; omission keeps
existing public/custom compiler behavior and existing cache identities. Either
explicit value requires a matching installed custom compiler and tool key,
recorded compiler support for `stable-mono-cgu-partitioning`, exporter support,
and a matching physical light wrapper. The existing stable-module selector
must be off. Both explicit modes have independent `stable-mono-cgu:off/on`
workspace and prepared-std namespaces, separate from legacy module-off.

The shared wrapper router appends exactly these two flags to native host,
guest and informational compiler invocations:

```
-Zstable-cgu-partitioning=no
-Zstable-mono-cgu-partitioning=no  # explicit off; yes for on
```

Selected exports still use the original argv when entering the exporter, so
the shared transformation runs once. Native helpers and proc macros retain the
light wrapper. Its existing physical compiler/sysroot check applies to all
custom compiler invocations. Required checking, dependency MIR retention, Cargo
units, profiles, backend/linker job flags and standard preparation flags are
unchanged. The compiler's own ordinary codegen dependency tracking decides
reuse. The function cache remains compatible, including `auto`.

Explicit per-item mode rejects module-on, custom Cargo, worker, macro-on and
borrowck-cache combinations. It rejects response files, user-supplied CGU
policy flags (including split `-Z` and underscore spellings), frontend/all-role
worker flags and proc-macro execution strategy flags. Launcher preflight checks
visible environment flags before std setup; the compiler router checks actual
Cargo argv, including flags from Cargo configuration. Existing inherited
wrapper overrides also fail this explicit mode. Future worker/macro selector
attributes are checked without requiring those experimental branches here.

New compiler imports record the actual `-Zhelp` text, hash and anchored option
names in `identity.unstable_options`, covered by the existing full identity
key. Existing compiler manifests without that field still load unchanged and
are never probed, rewritten or assigned new capabilities. In particular, the
old installed stable-module compiler cannot select either explicit per-item
mode. Importing the same package again through the new importer would produce
a new identity containing its actual help, not add support to its old key.

Custom tool publication probes the actual adjacent wrapper with
`--rust-interp-stable-mono-capability`. Its std-only output is the versioned
routing policy and the sysroot baked into that binary, on two lines. The
publisher requires exact equality with the selected compiler prefix and binds
the wrapper SHA256 in `capabilities.json`; the exporter sysroot, tool composition
and binary manifest must also match. Normal launcher invocation does not run
this publication probe. Launch receipts record the mode, namespace, both flags,
compiler-help digest, wrapper identity and unchanged job/std flag policies.

The prepared tests add three Rust route controls, two importer/legacy identity
controls, and six mocked launcher/publication controls. They cover all native
crate roles and guest metadata, existing export selection, exact flag count,
non-Unicode/invalid policies, physical wrapper and exporter disagreement,
old compiler rejection, no child launch on preflight failures, three distinct
cache namespaces, std namespace propagation and preserved function-cache auto.
All remain unrun until the canonical lock admits qualification.

Integration handoff: the source-path-v2 helper accepts existing custom and
namespace arguments plus `policy='source-paths-v2', prepared_key=...`. Preserve
its policy/key arguments while selecting the namespace from this new selector;
its preparation CLI can use either exact per-item namespace. This branch does
not change that helper or introduce a full screen. Future qualification must
use a genuine new production compiler with actual option support, prepared std
v2, strict complete compiler-provided diagnostic snippets, real native and VM
cold/edit/restore controls, and finally one same-compiler off/on/off27 screen.
The stable-module policy stays off in every arm. The assertions-enabled old
compiler is not a paired performance baseline, and holdouts remain untouched.
