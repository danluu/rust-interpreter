# Empty and forwarding call candidates in real test traces

The current guarded artifacts contain calls that meet narrow structural and caller-memory checks without expanding caller frames. This is read-only candidate discovery, not an optimization or a speedup measurement. Every decoded operation is checked against the matching execution profile.

| Workflow | Direct calls | Proved empty unit calls | Proved forwarding calls |
|---|---:|---:|---:|
| fre-folded-literal-trie | 39,809,688 | 1,549,104 | 2,133,534 |
| fre-word64 | 23,300,992 | 162,136 | 1,533,774 |
| fre-word64-inline8 | 8,778,797 | 162,136 | 618,570 |
| pgrust-sha1-inline8 | 1,081,860 | 81 | 0 |

An empty candidate contains exactly Return and has a zero-size result. A forwarding candidate contains only local-address definitions, one direct call and Return, with exact ordered argument size/offset correspondence, the same result size and slot, nonoverlapping wrapper formal/result ranges, and no forwarding cycle. All counted caller sites pass the existing inliner local-extent proof. There is no function-name allowlist.

For example, the frequently called byte-splat wrapper receives one byte at offset 16 and returns sixteen bytes at offset 0. Its target has the same argument/result layout, so bypassing the wrapper is structurally plausible. The target itself has a 49-byte frame and 62 operations after existing inlining; it must not be mistaken for a single primitive operation.

Any implementation still needs independent correctness checks for aliases, result/argument overlap exclusions, register redefinition, branches, zero-size endpoints, caller-location arguments, function handles, indirect calls, failure paths and transformed-IR instruction budgets. Argument evaluation must remain. Resource costs and frame addresses can change as with existing compiler inlining; a runtime shortcut would instead need to preserve runtime budget semantics.

The counts are observed calls in these selected original-test workflows. They neither predict saved CPU time nor establish whole-application support. The actual scratch-frame experiment is being rechecked before choosing another compiler change.

[CPU evidence](../folded-trie-guarded-cpu-sample-01/summary.md), [identical-tool calibration](../identical-tools-aa-e2e-01/summary.md). Exact decoded layouts, call sites, hashes and inspector provenance are recorded in the linked JSON paths.
