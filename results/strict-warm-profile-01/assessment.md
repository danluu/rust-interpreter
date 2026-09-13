# Strict warm-build compiler diagnosis

One real production edit in the pinned nushell `type-relations` workflow, with all 14 original tests preserved. The empty-target prime, edited source and restored original each passed the selected suite. These are diagnostic observations, not a performance comparison or evidence that the 0.5 s target passed.

| State | Cargo wall seconds | VM seconds | rustc phase logging |
| --- | ---: | ---: | --- |
| prime | 67.365320 | 0.275745 | disabled |
| edited | 6.069688 | 0.012762 | enabled |
| restored | 5.030392 | 0.013068 | disabled |

All states include the diagnostic Python wrapper, verbose Cargo output, Cargo HTML timings and exporter timers. Only the edited state adds rustc phase logging. The edited and restoration commands have different source/cache histories, so their difference does not estimate instrumentation overhead. Tool/bootstrap and prebuilt standard-library setup are outside these observations. The direct Cargo-to-artifact metric excludes launcher startup and VM preflight; it is not strict readiness.

The edited command has 18 compiler units, 1 build-script execution and 5 compiler information probes. Cargo reports 19 timed units. The selected exporter reports 1.280312 s frontend and 0.042150 s lowering; other required units remain outside those scopes.

## Every edited compiler unit

Host/target context, Cargo feature sets and actual emissions remain distinct. The selected test is identified through its captured exporter arguments and the selected Cargo artifact, including its `cfg(test)` configuration; checking only the incoming argv for `--test` would mislabel it.

| Package | Actual role | Context | Features | Child wall s | Cargo IDs |
| --- | --- | --- | --- | ---: | --- |
| nu-protocol | ordinary library check | explicit target | default, os, os_pipe | 1.386204 | 417 |
| nu-protocol | host library build | host context | os, os_pipe | 1.799660 | 416 |
| nu-engine | ordinary library check | explicit target | os | 0.209373 | 405 |
| nu-heavy-utils | ordinary library check | explicit target | endian, merge, yaml | 0.153930 | 410 |
| nu-json | ordinary library check | explicit target | linked-hash-map, nu-protocol, preserve_order | 0.130799 | 411 |
| nu-parser | ordinary library check | explicit target |  | 0.255033 | 412 |
| nu-color-config | ordinary library check | explicit target |  | 0.100946 | 400 |
| nu-table | ordinary library check | explicit target |  | 0.133762 | 422 |
| nu-cmd-extra | host build-script compilation | host context |  | 0.257651 | 396 |
| nu-cmd-base | ordinary library check | explicit target |  | 0.099402 | 393 |
| nuon | ordinary library check | explicit target |  | 0.111803 | 445 |
| nu-std | ordinary library check | explicit target |  | 0.079205 | 419 |
| nu-cmd-lang | ordinary library check | explicit target | os | 0.150789 | 397 |
| nu-command | ordinary library check | explicit target | aegis-password-generator, crossterm, getrandom, js, notify-debouncer-full, open, os, os_pipe, rand, reedline, uu_cp, uu_mkdir, uu_mktemp, uu_mv, uu_touch, uu_uname, uu_whoami, uuid, which | 1.169905 | 401 |
| nu-cmd-extra | ordinary library check | explicit target |  | 0.203288 | 394 |
| nu-cli | ordinary library check | explicit target |  | 0.234723 | 392 |
| nu-test-support | ordinary library check | explicit target | nu-cli, os | 0.153663 | 424 |
| nu-protocol | selected library test check | explicit target | default, os, os_pipe | 1.454664 | 418 |
| nu-cmd-extra | build-script execution | Cargo run-custom-build |  | 0.280000 (Cargo interval) | 395 |

Compiler child wall intervals and Cargo intervals have different boundaries and can overlap. They do not sum to CPU or complete-command time. The preserved Cargo timeline includes every reported interval and unblocking edge; it does not expose a complete causal critical path.

## Phases in the four longest compiler invocations

Each cell aggregates events with that exact label within one invocation. Nested phase labels overlap and must not be added into a total. Missing selected-exporter `total` output is left missing.

| Package / role | Macro expansion s | Type checking s | Misc checking 3 s | Metadata s | Borrow checking s |
| --- | ---: | ---: | ---: | ---: | ---: |
| nu-protocol / host library build | 0.271059 | 0.093163 | 0.253283 | 0.316879 | 0.032612 |
| nu-protocol / selected library test check | 0.400319 | 0.185419 | 0.163188 | not reported | 0.027566 |
| nu-protocol / ordinary library check | 0.276190 | 0.094655 | 0.242357 | 0.190162 | 0.035787 |
| nu-command / ordinary library check | 0.172556 | 0.173179 | 0.022969 | 0.274692 | 0.031209 |

## Incremental-cache scope bounds and repeated events

| Package / role | Persist s | Serialize s | Outside serialize s | drop_ast events | drop_ast sum s |
| --- | ---: | ---: | ---: | ---: | ---: |
| nu-protocol / host library build | 0.105209 | 0.093124 | 0.012085 | 22887 | 0.035690 |
| nu-protocol / selected library test check | 0.082910 | 0.053438 | 0.029473 | 28286 | 0.038054 |
| nu-protocol / ordinary library check | 0.082875 | 0.072140 | 0.010735 | 22887 | 0.033605 |
| nu-command / ordinary library check | 0.114134 | 0.073893 | 0.040241 | 13254 | 0.024534 |

On the pinned compiler, the outer result-cache persistence scope includes cache promotions, closing the old memory map, file setup/finalization and the nested serialization scope. The difference is an observed upper envelope for promotion inside that invocation, including other work and timing effects. It is not pure promotion time or a predicted removable speedup. The JSON retains count, sum, minimum and maximum for every repeated phase label. The table keeps every occurrence instead of overwriting repeated labels. These counts make the logging cost relevant, but they do not measure that overhead.

## Evidence and scope

Source revision: `9d3157963241cf89447119d34d6e887859f5e7e8`. Tool key: `923ad6d94c365365f15322ee65d32dca6ba9ccc4fd07a8147111329ea1955c86`. Cargo workers: 4; suite workers: 2; borrow-check reuse: `off`; function reuse: `auto`.

The summary preserves tool binary/capability/source hashes, compiler identity, source-state hashes, all metadata-sysroot hashes, measured harness hashes, selected-artifact hashes, test outcomes and verified restoration/input-integrity receipts. [summary.json](summary.json) contains the complete aggregates and roles. [report.json.gz](report.json.gz) preserves the exact original report bytes, including every original compiler argument and phase event, with deterministic gzip metadata. No project target artifacts are copied into results.
