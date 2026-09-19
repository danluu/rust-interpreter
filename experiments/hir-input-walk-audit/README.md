# Single-Walk qualification variant

This is a **source-only, uncompiled, unrun audit proposal**. No compiler, test,
application or benchmark has been executed. Its separate compiler identity is
ineligible for every timing comparison. It must never replace the performance
candidate in an application measurement.

The input is the committed single-Walk artifact at
`e4e7ac4ece88181f36f3ad9222e22a9eeb4506ca`, based on compiler
`7efc0d9484da82cd327deb3b48616f8ec81eaf8d`. Apply its unchanged
`7724d95c…` candidate patch first, then this directory's `source-01/audit.patch`.
The generator checks the full inherited 24-file identity closure, changes only
the two body-cache modules and the acyclic source identity, and writes separate
copies. It does not edit either compiler checkout or the performance candidate.

For every actual AST that passes the existing input gate, the audit constructs
the new private `ProbedInput`, then invokes the **exact old `current_nodes`
function copied byte-for-byte from the base Git blob**. That function performs
its original second traversal and compares the two normalized `Input` byte
streams. The audit then compares its returned ordered node vector with the
new constructor's vector. A repeated-traversal error, byte disagreement or
node-order disagreement fails the audit compiler immediately. No fallback,
environment variable or option can disable those comparisons.

The existing `-Zincremental-info` option controls success/rejection messages
only. Assertions run with it both on and off. Coverage compilations require
one exact success message for each named accepted function and positive
parameter/body/trait/external-reference counters where appropriate. Separate
info-off compilations compare complete JSON diagnostic bytes without filtering
or rewriting audit output. The unchanged capture/reuse enable gate still
controls whether ordinary body-cache preparation is entered at all.

`source-01/fixtures` is a proposed run-make test directory. It preserves the
base `hir-body-cache-capture/fixture.rs` and its entire existing `rmake.rs`
unchanged, invoking those original controls before the new controls. That
retains original edit, restore, trait-resolution, corruption, lint, diagnostic
and compiler-version-override assertions. The additional real source fixtures
cover the following fixed expectations in both capture and reuse modes:

| Input | Required observation |
| --- | --- |
| Escaped UTF-8 strings, byte strings including `0xff`, C strings, chars and bytes | Accepted actual AST; ordinary execution assertions pass |
| Raw string, byte-string and C-string forms | Accepted actual AST and unchanged values |
| Underscored decimal, float, hexadecimal, octal and binary literals | Accepted actual AST and exact runtime values |
| Mutable/ref local patterns, wildcards and shadowing | Accepted AST with nonzero parameter and body node counts |
| Local constants/statics, function calls and tuple constructor | Accepted actual resolutions and unchanged behavior |
| External module constant | Accepted AST with nonzero external-resolution count |
| Imported trait candidate and method lookup | Accepted AST with nonzero trait-entry and candidate counts |
| Typed local, nested item, closure, match, tuple parameter, coroutine, explicit path arguments, external call and expanded macro | Exact named rejection reason; ordinary behavior still passes |
| 131,073-byte literal; owner over 262,144 bytes; 4,200 expression statements; 130 nested parentheses; 4,097-byte identifier | Exact existing literal, source, node, expression-depth and identifier budget rejection |
| Invalid numeric suffix, invalid escape and overflowing integer | Compilation fails with identical unfiltered JSON diagnostics in off/capture/reuse modes |

Each added raw and coverage compilation has a separately named, initially
absent incremental directory, so a reused whole-crate result cannot silently
replace coverage. The info pass checks literal normalized bytes and actual
node order inside the compiler; the fixture does not reproduce or simulate
the walker in another language. Existing incremental histories remain within
the inherited controls. Coverage expectations are unqualified until the
compiler runs; a mismatch is a retained qualification failure, not permission
to drop the fixture or relabel its result.

This packet does **not** claim source fixtures exercise every defensive gate.
Duplicate/dummy node IDs, fabricated resolver inconsistencies, placeholder
parameters, and parented AST spans cannot be reliably requested with these
ordinary Rust inputs. Their checks remain byte-identical in the first walk;
actual coverage would need a separately reviewed compiler-internal control
using real parsed inputs. Macro hygiene is explicitly covered, and rejected
lexical input is a diagnostic control rather than proof that an invalid AST
reached `probe`. Interner occupied lookups may reserve/reallocate their table;
the audit deliberately retains the baseline second traversal, including that
bookkeeping and duplicate internal numeric debug traces. It is therefore not
a speed measurement of the single-Walk candidate.

The next step is source review of this patch and fixture recipe. Any future
compiler build needs a separately reviewed isolated source/toolchain plan,
the canonical workload lock with a 600-second admission bound, unchanged
24/9/8 GiB build limits, retained compiler/test output, and an explicit audit
tool identity. Run existing lowering controls and this complete run-make
directory before considering the audit qualified. Later performance work
must use the separately built performance identity, preserve its ordinary
strict application assertions and negative controls, and exclude all audit
compiler measurements.
