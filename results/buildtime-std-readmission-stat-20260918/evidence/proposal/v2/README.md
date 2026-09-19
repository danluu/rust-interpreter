# V2: one stat only where the predicate's error policy is known

This is an unapplied source proposal against the immutable C6 publication base f38004cbd3392b5a6763f920d80801826bbde77c. No module imports, tests, workloads, compiler queries or performance measurements ran. The C9 worktree remains under the parent's ownership.

V1 is preserved intact in the parent proposal directory and is not acceptable: its retry fallback could hide an initial transient OSError/ValueError if the next lookup succeeded. V2 removes that retry completely.

A module-level guard enables the fused observation only when sys.implementation.name is cpython, sys.version_info[:2] is exactly (3,14), and os.name is posix. This targets the locally inspected CPython3.14 POSIX public predicate semantics without assuming them for earlier/future minor versions, other implementations or platforms. All those other runtimes retain the original is_file()/stat sequence literally in the else branch.

On the enabled path, one Path.stat is attempted. OSError or ValueError is caught once, and the unchanged artifact RuntimeError is raised after leaving that handler, with no retry or added exception context. A successful stat must pass stat.S_ISREG, and its same result supplies the original device/inode/size/mtime stamp. Regular-target symlinks remain followed.

local-version-proof.json binds the exact installed Python3.14.7 pathlib/__init__.py, genericpath.py and posixpath.py source hashes and relevant ASTs. They show Path.is_file delegates to os.path.isfile when following links; POSIX imports genericpath.isfile without an override; that function catches all OSError/ValueError from os.stat and otherwise tests stat.S_ISREG. Path.stat delegates directly to os.stat with follow_symlinks=True by default. These are read-only local primary-source checks; no target or stdlib module was imported to create the proof.

production-ast-diff.json records the exact guard and before/after loop. Removing the sys import and guard, then replacing the initial loop with its original AST, makes the whole module AST equal. The other-runtime else body is AST-identical to the original initial type/stamp sequence. All production text after the loop is byte-identical, including all comparisons, eligibility checks, full hashes, fd checks, receipt validation, final path/ready checks and receipt publication.

The source does not promise identical outcomes for an adversarial replacement timed strictly between the old two successful stat observations. It does preserve the original initial-error outcome, which v1 did not, and it retains every downstream mutation/integrity check. The caller's existing lock and immutable-artifact assumptions remain in force.

## Semantic coverage

The seven original tests and helpers are unchanged. V1's four added semantic tests are also unchanged: actual nonregular and broken-link errors, followed regular symlinks through hash/receipt/direct reuse, stable native-pathlib errno policy, and cross-artifact exception order.

The fifth new test injects a one-shot ENOENT, EACCES, EIO or ValueError for the named artifact. It independently resets that fault for the public Path.is_file error oracle and the actual validate call. Validation must report the same native-policy error, preserve cause/context and leave ready/receipt state unchanged even though a hypothetical later stat would succeed. It does not assert how many calls occurred. This test directly rejects v1's retry behavior.

There are twelve tests per arm,24 paired executions. A future qualification should run the same twelve-test module against each actual production arm, with canonical import selection, on pinned CPython3.14 and the available older interpreter if the parent elects that controlled compatibility check. Do not simulate older runtime behavior by changing the optimization flag and call that real compatibility coverage.

## Measurement remains unfrozen

The draft two-case,26-artifact synthetic validation design in std-readmission-stat-probe remains held pending v2 review and application. Its proposed numerical thresholds have not changed and no data exists. Its source/test bindings must refer to v2 and24 tests if accepted; the applied-source and successful-unit hashes remain UNBOUND.

The proposed measurements expose actual validate on matching saved stamps and on an existing actual readmission receipt, with bounded synthetic payloads and the retained path/count shape. All process CPU/wall/RSS guards remain required. A component result cannot support a whole std-setup, build/export or holdout claim, and a small absolute gain may fail those guards. There is no reason to expand the panel or retime an unchanged candidate to force a win.
