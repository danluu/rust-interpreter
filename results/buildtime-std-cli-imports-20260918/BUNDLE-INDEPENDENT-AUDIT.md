# Independent publication bundle audit

PASS. This note records completed read-only checks 39883d, 6c4e67 and cb46d3; it is outside the frozen evidence bundle. No workload, test, compiler query, project import or Git mutation was performed for this audit.

Final identities:
- artifact-manifest.json: 8768b616b0df9bdceb156d4830ed5d4603988841caeea5f7d3a14c253863c0a9.
- README.md: 05429a0a115e604b66f2c6851d4974fe012059fc23cc89c20e266b00e3ea5699.
- summary.json: 8310cdae12ef1e3fae06181492ea0894e2ea083ef7df5dc23a33120a1904e86f.
- raw/all-stage-files.jsonl.gz: 4daa54a01c4a35020529436c59dbe40597b312452a37de4a08f0644a780d90dd.
- Original timing result: c7185d5ee410e22976dbbbb8a6161c92c03824f8d5a795dd4fcd8a05c50a72f0.

The 104 bundle files total 7,858,364 stored bytes. The manifest binds 103 entries and excludes itself; their decoded total is 52,624,659 bytes. Every stored/decompressed length and SHA matched. All 99 original-backed entries matched their original bytes. All 792 full-payload archive records independently decoded to exact original bytes and matched the index, with 53 unchanged directory identities and complete stage inventories: unit 16 files/3,916,888 raw bytes, fixture 45/4,898,061 and screen 731/19,772,624. All 192 child stdout/stderr files across the 96 total stage children are included. Direct compressed result files also restore exact original receipts. No deduplicated payload format or omitted records were accepted.

Independent pinned-Python recomputation matched the exact 46-row/92-child timing schedule, all 100 paired ratios and every summary field, all eight frozen gates and whole-process CPU identities. Component CPU ratio is 0.9611748859388262 with 18/20 strict wins; component wall 0.9608166871415679, whole-driver CPU 0.981114850411019, wall 0.9796900833178188 and RSS 0.9937866684821178. Published summary/gates exactly equal the original result. The 21 successful candidate test IDs, 47-entry/36,370-byte synthetic fixture, 72-file/1,843,874-byte cache, 101 dependency proofs and 2,448 source/runtime bindings match their retained receipts.

Source comparison verified the original patch e5df711ee51cc0e53d255af38d19d2a88e5b6112727ecd2fe702dc3f083dbb23 and exact inverse of the two conditional imports. All 190 Python files in /Users/danluu/dev/rust-interp-std-cli-import-publication-20260918 matched the measured candidate bindings; both intended source files matched the bundle. Its recorded integration is from measured 050a7d2a1e9677bc467a49fdba7a2ab485566e97 to publication base 390ecf2dd5b25f9004cd452a6c70f71072a78a3f. The parent separately reported upstream advance to 1f2f4e41 and source-equivalence check a60778; that later Git integration was not independently repeated by this bundle audit and remains the parent's pre-push responsibility.

README claims stay within actual stock standalone std_mir import/main and prepared reuse on 26 synthetic artifacts, with compiler identity discovery stubbed. It discloses the timed audit hook/common wrapper, candidate-only tests, process-level harness work and absence of general build, interpreter-launcher or holdout evidence. The final one-sentence clock clarification correctly distinguishes driver work from parent checks outside both clocks. Its previous README/manifest were preserved outside the bundle; only that README entry and byte totals changed, while all other evidence remained identical. No timing sample was repeated, replaced or excluded.
