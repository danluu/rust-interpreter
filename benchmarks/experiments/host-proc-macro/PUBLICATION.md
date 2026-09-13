# Qualified public toolset publication contract

Status: proposed contract for root review; no build, publication or screen has
executed under this plan. Production source remains `01e36c0426afbd61bbfe540af6673a5e7db2f87c`.

`planned-build-01.json` is superseded and **was not executed**. Retain its exact
bytes (SHA-256 `8108e3de7cdf9cd80fc7382824be639d7cf8e20a46535729b392f552a390b068`).
It incorrectly treated an ordered source fingerprint as a complete tool key.
`planned-build-02.json` is also retained unexecuted; subsequent support changes
invalidate its frozen harness hashes. The final runner plan uses the fresh
`.work/host-proc-macro-build-03` directory. It does not authorize resuming or
interpreting an old plan as a completed run.

## Two distinct identities

The existing fingerprint
`f77229fac75b617de4cc760a8e509015e48e7442462f4276c250c7d4e382e23a`
is `source_input_key`. Reproduce it by hashing, in the plan's explicit
`source_input_paths` order, each UTF-8 relative path, one NUL byte and its exact
file bytes. There is no additional delimiter between entries. These paths cover
the root Cargo manifest/lock and the two tool crates' Rust files/manifests. The
additional `workspace_sources` inventory binds every regular file in all four
workspace crates, the root manifest/lock and `rust-toolchain.toml`, including
workspace correctness-test inputs. Reject unresolved source symlinks. Preserve
the exact source bytes as well as their inventory; a Git revision alone does not
bind a dirty checkout, local build script or test input.

The **actual `tool_key` is unknown before the build and qualification**:

```python
tool_key = hashlib.sha256(json.dumps(
    composition, sort_keys=True, separators=(',', ':')
).encode()).hexdigest()
```

Use the existing `custom_compiler.digest` canonical JSON convention, including
its default ASCII escaping. Hash file payloads as exact bytes. Use lowercase
64-character SHA-256 strings, normalized relative payload paths, no `..`, and
no symlink payloads. Do not use the source fingerprint as an installation key,
predict binary hashes, or invoke automatic source-key tool setup for this run.

## Composition schema

`source.json` is an envelope with `tool_key` and the following `composition`.
Every field below is required. The composition contains no final tool key,
installation destination or hash of its own envelope.

```text
schema_version: 1
kind: "qualified-public-toolset-v1"
source:
  revision: frozen production Git revision
  source_input_key: ordered source fingerprint
  ordered_paths: replacement plan's source_input_paths
  files: replacement plan's workspace_sources (relative path -> SHA-256)
public_compiler:
  toolchain: "nightly-2026-09-08-aarch64-apple-darwin"
  target: "aarch64-apple-darwin"
  source_revision: "cea272fa356e94bd2ee2cadf376630aa0683867a"
  sysroot: exact absolute public rustup sysroot
  rustc_path: exact absolute public bin/rustc
  rustc_sha256: actual binary hash
  version_stdout_sha256: exact successful rustc -vV stdout hash
  input_inventory_sha256: provenance/compiler-inputs.json hash
public_cargo:
  path: same public rustup installation's absolute bin/cargo
  binary_sha256: actual binary hash
  version_stdout_sha256: exact successful cargo -vV stdout hash
build:
  plan_sha256: exact replacement plan bytes
  profile: "release"
  environment_overrides: exact plan overrides, including CARGO_PROFILE_RELEASE_DEBUG="1"
  command_records_sha256: provenance/commands.json hash
  dependency_inventory_sha256: provenance/dependencies.json hash
  harness_inventory_sha256: provenance/harness.json hash
libraries:
  manifest_sha256: provenance/libraries.json hash
  platform_sha256: provenance/platform.json hash
binaries:
  rust-interp-vm: actual binary hash
  rust-interp-mir-export: actual binary hash
  rust-interp-rustc-wrapper: actual binary hash
capability_stdout_sha256: exact successful capability stdout hash
correctness_receipt_sha256: provenance/correctness.json hash
payloads: complete relative provenance path -> exact payload SHA-256
```

`payloads` must include each referenced JSON/output and all supporting source,
harness, command receipt, stdout/stderr and real-fixture command/validation
records. Include the replacement plan, this contract and the profile amendment.
Store source and harness bytes under separate `provenance/source/` and
`provenance/harness/` prefixes; their inventories map original relative names to
those exact bytes. The manifest must be sufficient to reconstruct each source
fingerprint and validation association from an archive without reading a live
checkout. Large compiled artifacts and dependency/sysroot binaries may remain
in owned storage with exact path/size/hash inventories; never describe those
hashes as archival retention of the binaries. The three published binaries are
present in the installation but need not be duplicated in a Git evidence archive.

Compiler inputs cover the actual public sysroot libraries consumed by exporter
compilation/linking and qualification, including rustc_driver and relevant
Rust/LLVM runtime files. Record the prepared public std's complete identity,
ready-file hash and input inventory used by the real histories in correctness
provenance. Require its compiler/target to match this public compiler. The
dependency inventory binds Cargo.lock and the actual resolved registry/path
sources, features and checksum/tree inventories used by the build, not merely
package names. Record effective Cargo configuration, wrappers, RUSTFLAGS and
the clean environment; unexplained inherited overrides fail qualification.

`libraries.json` records the transitive non-system dynamic-library closure of
the public compiler, public Cargo and all three resulting tool executables:
logical and resolved paths, sizes, hashes, stat snapshots, dependency/rpath
edges and the exact metadata command receipts used to resolve them. Include
Homebrew libraries if reached. Unresolved or ambiguous non-system edges fail
publication. `platform.json` binds architecture, macOS version/build and the
system dyld-library assumption. Verify hashes and resolution at build capture,
qualification completion and screen admission; guard resolution/stat identity
through the history and fail on any change, requiring fresh qualification.
The current implementation rejects changed stamps even if bytes might still
match; it does not implement a rehash-and-accept fallback. Changing an external
library cannot silently retain readiness. This is a required supervisor/publication check;
the existing launcher binary-hash check alone does not implement it.

## Qualification and acyclic publication

Run the replacement plan's reviewed build/test commands in the agreed lock window.
Record additional read-only identity-collection commands and their outputs in
the provenance command index; they do not replace any required qualification.
Retain child identities and always wait for started children if publishing a
receipt fails. The Rust workspace tests and release build must succeed with the
same source, public compiler/Cargo and DEBUG=1 profile. The three launcher
contracts, 24 screen contracts and all three real histories must pass; real
histories must report zero skips and exercise the VM. Record individual Rust
suite counts/ignored tests and compare to the frozen source inventory rather
than inventing a total in advance. Retain the ordinary native checks, semantic
flags, full Cargo history, edits/restoration and selected bytecode-equality
controls described by the frozen fixtures. No benchmark result is a substitute
for these correctness checks.

`correctness.json` is written **before** computing the composition key. It has
`schema_version: 1`, `status: "passed"`, the source input key, replacement plan
hash, exact three-binary hash map, compiler/Cargo/library identity hashes,
capability stdout hash, shared std identity, each required command's receipt
and output hashes, and explicit suite/history results. It must contain no final
tool key or publication path. Verify these fields against the referenced bytes
and actual commands; the word `passed` alone proves nothing. Capture the final
binary/source/input hashes after qualification and reject any change during it.

Then construct the composition, hash it, and publish to fresh owned
`.work/interpreter-tools/<tool_key>` directories. Neither the original source
key directory nor any existing installation is overwritten. Both the build
owner and screen owner receive identical source/provenance/binary bytes.
Per-owner installation paths/stat guards belong in a separate publication
receipt, which references the computed key and is not an input to that key.

Keep `ready.json` compatible with `installed_tools`: exactly the three binary
names mapped to hashes. Produce `capabilities.json` from parsed retained
exporter capability stdout, adding only `tool_key` and `exporter_sha256` after
key derivation. Require schema 1, bytecode version 5, the public compiler
sysroot and `host-proc-macro-opt-v1`. Its other fields must equal the original
output. The composition binds the raw output, avoiding a capability/key hash
cycle. Publish readiness last after verifying every copy, hash, association and
guard. This is an explicit-key experimental publication contract; stock
automatic launcher key behavior is unchanged.

## Materializing the screen command

The source-only plan has `tool_key: null`, `screen_command: null`, no predicted
installation destination, and a non-executable `screen_request`. A future
publication supervisor materializes `screen-command.json` only after verifying
both installations, the integrated harness, the owned source clone and the
shared public std. It records the replacement plan hash, publication-receipt
hash, actual composition key and exact argv. Fill both tool-key arguments with
that same computed key. The argv structure is:

```text
<python> <screen-root>/benchmarks/experiments/strict-warm-build/screen.py
  --run-id strict-warm-proc-macro-screen-01
  --source <screen-root>/.work/sources/nushell-proc-macro-opt
  --candidate-policy host-proc-macro-opt
  --baseline-tool-key <published-composition-key>
  --candidate-tool-key <published-composition-key>
  --std-mir-ready <recorded-public-ready.json> --lock-wait-seconds 45
```

All arms use the same three binaries, public compiler/Cargo and std, with
off/on/off macro policy, independent project histories, no custom compiler or
Cargo, no borrow-check cache and no unrelated optimization. Preserve all 27
commands, all 14 tests and the 0.500-second gate. Neither qualification nor
publication sets `performance_claim` or final/holdout qualification to true.

The saved assessor must check this typed composition and each referenced
payload, rebuild the source key from retained bytes, reconcile actual build
flags and correctness results, and match raw capability stdout to its final
envelope. Checking only `digest(composition) == tool_key` would bind bytes
without proving that those bytes describe the required qualified public build.
Initial assessment checks actual frozen input identities; repackaging may use
the previously verified exact archive and must state that distinction.
