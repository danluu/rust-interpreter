# Host procedural-macro optimization: no established warm gain

The candidate median was 4.040219 s, against 4.083314 s for baseline and
4.009324 s for the independent baseline duplicate. Zero of five edited
candidate commands were below 0.500 s. Median paired wall change was -1.433%
and CPU change -0.631%; maximum A/A wall deviation was 16.229%. This screen
provides no reliable improvement or final latency/generalization claim.

All 27 commands, all 14 original tests, the expected wrong-result failures,
nine source states, bytecode/catalog equality and restoration passed. All
three arms used the same qualified public compiler, stock Cargo, tools and
prepared standard MIR. Only the explicit host proc-macro codegen policy was
off/on/off. No holdouts were evaluated.

The screen used source ca7318da. Its complete-command timings include normal
launcher, Cargo, compiler and VM work; no operational work was subtracted.
The 56 frozen-input audit records were independently assessed: admission,
before/after all 27 commands, and final. The benchmark's existing input-audit
boundary is unchanged.

`evidence.json.gz` contains 775 exact members. Root independently rechecked
all member lengths/hashes and both archive hashes. `assessment.md` supplies
all observations, cold setup times and the scope of the comparison.

`setup-support.tar.gz` retains 204 files with exact hashes in
`setup-support.json`: the merged 43-test Python run and its source snapshots;
source checkout preparation; the first screen's zero-command lock timeout;
the explicitly recorded run-ID-only retry; materialized argv; both screen
supervisor records; assessment receipts; and independent archive reviews.
It also preserves the earlier completed Cargo cache retirement. That
retirement kept all results/artifact copies and records ownership, inventory,
quiescence and free space. Its saved ps stdout is filtered to matching cache
paths, not a full process inventory.

The first admission preserved its fixed 45-second lock wait and failed before
source mutation or any benchmark command. Run 02 retained that failure and
changed only the run ID. No timed observation was discarded or replaced.
The completed build/publication qualification and earlier setup failures are
separately archived in `results/host-proc-macro-build-05` (source ca7318da).
