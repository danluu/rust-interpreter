# One structural walk for input and node order

This independent source candidate is **uncompiled, unqualified and unmeasured**.
It is based on compiler `7efc0d9484da82cd327deb3b48616f8ec81eaf8d` and does not
include the options-hash or packed-storage candidates. It is not adopted.

The existing body-cache preparation runs `input::probe` and immediately reruns
the same `Walk` in `current_nodes`. The second traversal rebuilds the same input,
serializes both copies and compares their bytes before exposing the AST node
order. This originally connected separately assembled qualification stages.
Both products already exist at the end of the first walk.

The candidate returns a `ProbedInput` with private fields containing that
walk's normalized input and its ordered nodes. Its sole constructor is the
successful end of the existing gate. The caller consumes both together.
Every original eligibility, span, resolution, literal, node-count and depth
check remains in the first traversal, in its original order. Later kind,
entry, key, journal, tree, preparation, cold-audit and poststate checks remain.
The cache key's encoding is unchanged apart from the required compiler-source
identity. No persisted pointer, previous compilation result or application
name participates in this invariant.

The old disagreement check is replaced by construction from a single walk,
not assumed to pass on benchmark inputs. The proof obligations below must
survive independent review and actual compiler qualification before any
performance comparison is meaningful.

## Source review

`source-01/proof` binds the exact source references; its manifest records their
SHA-256 hashes. `prepare_patch.py` also verifies all inherited identity inputs,
derives a new acyclic identity and changes exactly three compiler files. It
does not edit or build the original compiler.

- The only production caller invokes both old traversals consecutively with
  the same immutable AST function and resolver references. No lowering, query
  or user code runs between them. The accessed resolver maps and trait slices
  have no interior mutation; the resolver's separate `Steal` fields are unused.
- `Walk::node` creates both the normalized node ordinal and ordered-node entry
  at the same point, after duplicate/budget/resolver checks. `resolved` walks
  that order and reads current resolutions and traits. The candidate retains
  the completed vector directly, so it cannot disagree with those ordinals.
- Literal validation is not pure: decoded strings, byte/C strings and numbers
  with underscores can intern normalized contents. The first traversal still
  performs these operations in the same order. Repeating them uses the same
  session interner and returns the existing index without inserting a symbol
  or advancing its index. Its hash table can still reserve capacity before
  finding an occupied entry; removing the second call can avoid this allocation
  bookkeeping. Interned bytes and indices remain unchanged. Invalid literals
  retain the original rejection/panic boundary. The locked hash-table and
  literal-escaper sources are bound in `proof-supplement-01`.
- Numeric literal helpers contain debug tracing. Removing the repeated walk
  removes its duplicate internal trace events in a debug-logging compiler;
  this is not a promise of byte-identical internal logs. It does not remove
  compiler diagnostics or first-pass validation. The currently qualified
  compiler configuration disables debug logging.
- `def_path_hash` reads the current definitions or crate-store hash table; it
  does not execute a semantic query. Span access can track parent dependencies,
  but every accepted span is checked for no parent before position access.
  Rejected spans still encounter their first-pass checks. Source snippet reads
  and owner validation remain in `probe` and are not removed.

## Required qualification

No test has been run against this compiler patch. Before adoption:

1. Independently review the constructor invariant, all reachable side effects
   and the exact patch; reject any eligibility or diagnostic change.
2. Build the isolated compiler and run all existing lowering and run-make
   controls, retaining corrupt-record, current-tree, journal, wrong-identity,
   unchanged/edit/restore and diagnostic preservation assertions.
3. Exercise real accepted ASTs with escaped strings, byte/C strings, underscored
   integers/floats, patterns, local bindings, resolutions and trait candidates;
   compare the original two-walk result with the new constructor's normalized
   bytes and ordered nodes in a qualification-only audit. Include rejected
   syntax, invalid literals, hygiene, parented spans and resource boundaries.
   The audit must observe actual compiler inputs, not a hand-written model.
4. Run unchanged application assertions and intentional failures under the
   same strict recipe before measuring balanced edited-build histories.

This candidate only reduces preparation overhead introduced by the body-cache
experiment. It does not establish a benefit over cache-off compilation or a
route to the complete 0.5-second target by itself.
