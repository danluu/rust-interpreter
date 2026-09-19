# Options-hash plus packed HIR sidecars — generator draft

This directory contains **unrun source-generation and verification code**. No
combined candidate, patch, checkout, compiler, test or benchmark has been created
or executed. The existing options-hash compiler and both original proposals stay
unchanged. Generating source artifacts requires a separate review of these files.

The intended base is the exact compiled options-hash source
`4de35bdacef0e3cd18a66bc30b5459c19e09b118`, with identity `7c6bc028…`.
`bindings.json` pins 79 input records (4,318,376 bytes), their full SHA-256 and
seven-field identities, both original manifests, the completed compiler receipt
and audit, every affected source, and all 18 original packed02 hunk hashes.
The recorded compiler result is a historical build qualification; it does not
qualify this combined proposal or claim application readiness.

`generate.py` will read those exact inputs without Git or compiler invocation.
It applies the 17 non-identity packed02 hunks at their exact original positions,
with no fuzz or offsets, to copies in memory of the current source bytes. It
never copies the saved packed `mod.rs` over the current file: that would undo
the cached options hash. The complete current `context.rs` stays byte-identical,
and the `.as_u64().encode` call remains unchanged. The original repeated input
Walk remains; single-Walk is a separate candidate.

The obsolete packed-only identity hunk is skipped. The new identity is SHA-256
of compact, sorted JSON mapping the final **29** identity input paths to their
full hashes, excluding the identity file. This includes the options-hash context
and the four new session/storage inputs. The generated identity then joins the
complete **30-file** retained closure. No final identity is claimed in this draft.

Future output is exclusively the initially absent `artifacts-01/`: 29 base
files, 30 candidate files, exact generator sources, input provenance, original
hunk associations, combined patch and a final manifest. Inputs are bounded to
96 files, 4 MiB per file and 16 MiB total; output is bounded to 192 files and
16 MiB total. Writes are exclusive, file-fsynced and read back. Inputs and
generator sources are rechecked before writing and before the final manifest.
A failure leaves the partial directory for review; there is no cleanup or retry.

`verify.py` independently derives the expected result from the pinned packed
candidate bytes, restoring only the cached-hash call in its body module and
retaining the current context. It does not call the generator's hunk applier.
It recomputes the identity, exact changed-file set and patch, then verifies every
retained byte and file membership. Its eventual source verification report is
not Rust compilation, behavior or performance qualification.

The saved Ruff comparison motivates this candidate: 1,414 incremental files
were linked with HIR reuse versus 3 off, with session-preparation self times
0.383906 versus 0.000954 seconds. It is one continued instrumented pair from the
older compiler. There is no predicted speedup. Options hashing and packed files
leave macro expansion, resolution, typechecking and other frontend work intact;
overlapping profile spans cannot be added to claim sub-0.5-second readiness.

See `QUALIFICATION.md` for the required future source, compiler, lifecycle,
memory and application checks. These programs are deliberately not run yet.
