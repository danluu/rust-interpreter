# Owned cached-tree preparation for warm replay

This is an unapplied source proposal against the exact options-hash compiler
`4de35bdacef0e3cd18a66bc30b5459c19e09b118` at `/Users/danluu/dev/rust-interp-runtime-exporter-20260918/.work/hir-options-hash-compiler-01/source`. The frozen compiler, every provider, and the existing input-walk and packed-sidecar
proposals remain unchanged. No compiler, test, probe or benchmark was run.

At `prepared_replay.rs:67-68`, a decoded tree is validated and immediately passed
to `prepared::prepare`. That function clones the tree and repeats full validation
at `prepared.rs:81`, then clones it again into the expected tree at line83.
`validate::check` at `validate.rs:259-270` includes both the structural/reference
Check traversal and the exact journal Order traversal, with local sets/maps.

The proposed private `prepare_owned_replay` accepts the owned raw tree, performs
the first full validation, checks current_state, converts its values, and moves
the validated tree into BodyValues.expected. Conversion returns owned values,
so its temporary borrow ends before that move. Current stays immutably borrowed
throughout. The new CheckedTree::into_tree accessor only extracts raw owned
bytes/values; it grants no Current or materialization proof. The old
prepare(&CheckedTree, &Current) API and all its callers/tests are byte-identical.
That API must continue revalidating a tree that may have come from a different
Current. The warm call now omits one provably repeated validation and two deep
BodyTree clones per successful hit. First validation → current_state → conversion
order is preserved; allocation failure timing can change with removed work.

ReadyHit construction, replay_plan, exclusive commit, recorded events, full
recapture, tree equality and poststate assertions remain byte-identical.
Fallback remains before all context effects. No post-effect retry or unchecked
constructor is introduced. Cold capture/audit, entry keys, storage checksums,
options hashing and input traversal are unchanged. This changes decoded wire
tree preparation, independently of the existing AST input walk and packed I/O.

The saved Ruff diagnostic pair contains 1411 hit events; lower_to_hir self
spans were 0.467368480s with reuse and 0.295637937s without it. Those spans include
other work and predate options-hash. No separate cached-tree preparation timing
exists, so this source observation cannot establish the next-largest isolated
cost or a speedup. Macro expansion remains a larger overall self span. All exact
profile/source paths and hashes are in provenance.json.

The patch changes three semantic files plus regenerated source_identity.rs.
All 25 original acyclic closure members were read and rehashed; the new identity
is `b15371d2d4c95381528d29e5ade9a2a2fbdf01072c4fb83684c7cf4280860348`. Its full map, exact before/after hashes, preserved compiled-base
association and strict in-memory patch readback are retained in provenance.json.
No patch was applied to a checkout and no standalone candidate files were built.

Before adoption, compile this actual Rust candidate and qualify the inherited
lowering/interface/support/run-make, cold/warm and stale-current/corruption
controls. Add owned-path equivalence cases against the existing checked path,
including local/reference/order/kind/UTF-8/range failures. Confirm actual
unchanged/edit/restore diagnostics and RBC equivalence, intentional failures and
replay poststate/finalization behavior; synthetic fixtures alone are insufficient.
The current options-hash runtime and strict Ruff measurement stay first.
