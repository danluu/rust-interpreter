# Cache compiler identity discovery

Suggestion 4.3 identifies two rustc proxy invocations before each standard-MIR
command. Cache their verbose version and original sysroot for an explicitly
dated nightly in the normal rustup installation. This is launcher work; VM,
exporter, Cargo commands and checking remain identical in both arms.

The option is `--toolchain-lookup=cached` with `--std-mir`; default is `fresh`.
Cache entries bind environment identity, proxy paths and file stamps, rustup
settings, compiler executable, installation manifests and shared libraries.
Stamps include inode, size, mode, mtime and ctime. Fresh context and installation
checks precede reuse; publication requires stable repeated discovery. Malformed
records miss; custom tools, loader overrides and unfamiliar layouts use fresh
discovery. This local cache does not authenticate an untrusted installation.
Standard-MIR keys, source-lock hashing and every existing artifact stamp check
remain in place. Cargo still goes through its explicit pinned rustup command.

Rustup documents explicit toolchain precedence, configurable installation homes
and custom-toolchain Cargo fallback. Avoid bypassing those rules by resolving
Cargo ourselves: [overrides](https://rust-lang.github.io/rustup/overrides.html),
[environment](https://rust-lang.github.io/rustup/environment-variables.html),
[custom toolchains](https://rust-lang.github.io/rustup/concepts/toolchains.html).

Qualification before timing: cache-hit identity parity; compiler/library/proxy/
settings/environment invalidation; malformed and interrupted records; unknown
dispatch fallback; all launcher/harness tests; a real original/valid-edit/wrong-
edit/restored Cargo fixture with unchanged test assertions, identical bytecode
and strict uncalled type/borrow errors. No toolchain installation is changed.

Measure full changed-source commands on short workflows, using the same
immutable qualified tool in fresh, duplicate-fresh and cached arms. Pgrust is
the public primary; private rg-aot and a large frontend-dominated workflow are
mandatory guards. Freeze exact workloads, schedules, sample counts and gates
in WORKFLOW.md before any performance observation. Keep ordinary native
libtest and a Cargo-check reference. No unchanged-build claim or runtime
speedup follows from a launcher cache.
