# Worker public build03 and failed qualification01

Public build03 completed its eight recorded build/check commands and published
tool `7191cec48448ea59dd85f330a417074d07390e6a1b1bf4f33f75c8a8a1172c02`.
Its typed status remained **public build published; worker qualification pending**.
The separately admitted qualification01 stopped after27 commands and did not
produce a passing30-command receipt. No screen was run with this attempt.

The final command, `assembly-rejection-1`, returned101 with empty guest stdout
and correctly reported `assembly: unsupported terminator asm!`. The saved
qualifier expected `unsupported terminator InlineAsm`, so its string assertion
failed. Raw diagnostics, process records, admission/failure records and the
original source remain retained. This is a harness-expectation failure, not
evidence that assembly was executed or accepted; it also does not qualify the
remaining controls or turn the failed history into a passing one.

The independent Nushell source preparation passed: it cloned the owned donor's
pinned Git revision without hardlinks, checked out that exact revision, rejected
alternates/dirty state/generated target contents, and wrote the planned owner
marker. Its raw commands and outer supervisor are retained separately from the
compiler/tool and fixture outcomes.

`evidence.tar.gz` contains build03's top-level raw receipts/logs, metadata,
all409 content-keyed provenance payloads, both publication-copy manifests,
qualification01's logs/bytecode artifacts/final fixture and source hashes, and
the source-clone preparation. The three outer supervisor histories are included.
Every one of the285 frozen qualification source files is bound to a saved
publication payload or the successful159-test run02 source snapshot. Current
ROOT or WORKER source files were not substituted under the old plan. Tool,
compiler and native executable binaries, Cargo targets and caches are omitted;
saved bytecode artifacts are retained as requested. Binary identities come from
the original publication manifests rather than a new binary inventory.

`members.json` lists each archived member's exact source path, size and SHA256;
`summary.json` records the archive identity and explicit failed qualification
status. The gzip archive builder verified every member and rechecked all source
bytes while holding the canonical workload lock. `packaging-receipt.json` retains
its admission and completion. The first archive attempt's overly literal check
for a separately quoted `InlineAsm` token is retained with the corrected attempt;
it had no children and did not alter the original experiment evidence.

No compiler, test or benchmark was run by archival. No source, target, cache or
prior result was changed or deleted. This archive makes no30-command success,
worker speedup or sub-0.5-second claim. Later build/qualification/screen attempts
have separate identities and evidence.
