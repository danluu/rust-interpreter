# Body-v2 native development coverage

The qualified public diagnostic completed ordinary Cargo `check --locked
--offline --jobs 2 --package nu-protocol --lib --tests` on the unchanged owned
Nushell `9d315796` source. Default features, dev profile and Cargo configuration
were preserved. All normal compilation and checking completed; all 742 reports
were accounted for, with zero unexplained resolver-owner gaps. No application
source was edited. This is structural input coverage, not a performance result,
the strict 14-test workflow, a holdout, or a cache-hit qualification.

There were 726 completed compiler invocations and 16 probes. Of those invocations,
689 had incremental disabled: 615,358 owners, including 213,791 function/method
owners, were ineligible by construction. The 37 incremental invocations contained
70,997 owners and 26,469 function/method owners; 3,536 body records passed the
closed structural/resolved input gate. These are invocation-weighted counts,
not deduplicated functions. `summary.json` retains every role denominator,
first rejection and selected invocation; `coverage.json` in the archive also
retains all 457 crate-name/compiler-role groups.

| Incremental owner role | Accepted / owners |
| --- | ---: |
| Free function | 190 / 3,941 |
| Inherent implementation method | 1,102 / 4,600 |
| Trait method | 103 / 374 |
| Trait implementation method | 2,141 / 17,554 |

The diagnostic's `provided-trait-method` denominator includes required methods
without bodies; those receive the explicit `no-body` rejection. First rejections
are ordered gate observations, not estimates of gains from relaxing a guard.
The largest incremental rejections within function/method scope were owner
span/hygiene (13,022), unsupported expressions (3,840), incomplete path
resolution (2,156), nonroot hygiene (1,138), pending external direct-call proof
(785), and existing body-local definitions (746).

For each of the two normal `nu_protocol` compiler configurations:

| Owner role | Accepted / owners |
| --- | ---: |
| Free function | 17 / 155 |
| Inherent implementation method | 259 / 1,119 |
| Trait method | 34 / 96 |
| Trait implementation method | 172 / 3,696 |

That is 482 accepted body records among 5,066 function/method owners and 12,488
all owners per normal configuration. Their bodies total 29,817 source bytes;
their encoded inputs total 535,975 bytes. The separate `cfg(test)`, `harness=false`
configuration accepts 489 bodies: 19/1,015 free, 261/1,179 inherent, 34/97 trait,
and 175/3,888 trait-implementation methods. It contains 6,179 function/method
owners and 17,877 all owners; accepted bodies total 30,306 source bytes and
542,833 encoded input bytes. The exact role classifier recognizes `--cfg test`
as well as `--test`; no result was retrospectively reclassified or rerun.

Across the 37 incremental invocations, accepted body records contain 262,427
body source bytes, 3,388,833 encoded input bytes, 28,970 body AST nodes and 9,762
parameter AST nodes. The encoded representation includes the full owner source
and typed field/span/resolution records, so it is larger than body text. There
are 4,411 trait-map entries, 1,293 candidate records and 1,456 external-definition
references in those inputs; all counts preserve repeated invocation occurrences.

The gate records owner DefPathHash, StableSourceFileId, role, full owner source,
typed ordered AST fields, owner-relative root-hygiene spans, stable node
ordinals, parameter binding patterns/modes/current local resolutions, partial
resolution presence/base/unresolved count, current definition hashes, and exact
ordered trait candidates/import chains/ambiguity flags. Plain local/self
field, method and indirect-call bodies can pass. Bare external direct calls
remain rejected pending a live legacy-const-generic proof. Unsupported syntax,
new body definitions, body attributes and generated hygiene still fall back.
No project name participates in this gate.

The read-only `after_expansion` diagnostic cannot observe lowering's entry/exit
HIR IDs S/E, prove complete capture/replay state, or measure actual cache hits.
No body-cache codec or compiler patch has been implemented. The larger eligible
set establishes useful structural coverage; it does not predict latency savings
or establish safe cache materialization. The public driver previously passed
66 native controls, including actual external trait-resolution changes and
identical raw public diagnostics for uncalled type/borrow/const/panic errors.

Driver SHA256: `ae65fd5f5207e62c121ba070fe3e8dd8f6ecb2b2252235634e63e021cd3d1167`.
Gate SHA256: `6df8b5b4fe1c0c88f6c21acbbf0514a61b48173bd037456b7563755c50ca15d1`.
Driver source is frozen at `501d992e`; development runner source is `fc74f953`.
The original `source.json`/`CONTRACT.md` inside the source snapshot describe the
earlier unrun contract checkpoint; `diagnostic-source.json` and the actual native
build receipts bind the subsequently qualified implementation and fixture.

The archive retains all raw compiler reports, Cargo stdout/stderr, exact process
receipts, setup plan, source/config/driver/public compiler guards, frozen helper
and gate sources, and all 2,473 tracked Nushell source entries. The two source
symlinks are archived as inert link-text files with exact target/membership
proofs; no archive member creates a symlink. All archive members were read back
and hash-verified under the canonical workload lock. Generated binaries, Cargo
targets and caches are excluded. Prior v1 and native fixture evidence remain
linked by archive hashes in `summary.json`.

Archive: 3,282 members, 16,962,808 bytes. SHA256:
`d89dba548d6cb77d789787906b40726de1f606c0e0ea9cd83c93988155dea0c9`.
