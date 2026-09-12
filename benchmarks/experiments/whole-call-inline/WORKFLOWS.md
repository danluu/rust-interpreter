# Fixed whole-call edit workflows, generation 02

The first generation stopped at disk admission. Run
`whole-call-aa-01-folded-literal-trie` launched no benchmark child, edited no
source and produced no timing pairs. Its failed admission and exact driver
remain in `results/whole-call-aa-01-folded-literal-trie/`.

Generation 02 changes run identities only. Keep the PLAN.md gates, tool hashes,
three cycles of five real edits, native controls, independent Cargo-check floor,
eight-GiB command floor and full preflight reserve unchanged. Order is A/A
folded, A/A token, candidate folded, candidate token. Preserve all fifteen pairs
per phase. A/A requires identical compiler/runtime and bytecode; the candidate
requires the exact qualified changed compiler and runtime with unchanged wrapper.

`check_workflows.py` must pass as `whole-call-workflow-controls-02` before the
first timed command. `record_workflow.py` binds terminal receipts after each
phase. `report_primary.py` recomputes all histories into `whole-call-primary-02`.
Token must improve wall time by at least 10%, reduce CPU and exceed the fresh
identical-tool envelope; folded wall and CPU must each stay within 5%. A failed
fixed gate parks the candidate, without tuning retries. Full native/TLS/fre
qualification and all seven separate held-out guards precede integration.
