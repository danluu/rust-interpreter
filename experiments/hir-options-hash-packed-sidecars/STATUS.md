# Combined source composition verified

The options-hash plus packed-sidecars source artifacts were generated and independently verified on 2026-09-18. The source identity is `e4d112c506f7b091c0e471c56ce25a1a8f62725ffa5676f7c977e105a1e450c0`, derived from 29 identity inputs and a complete 30-file closure on the exact options-hash base `4de35bdacef0e3cd18a66bc30b5459c19e09b118`. The combined patch SHA-256 is `8994a0af4060a5753bb0fb5410dc17e9d1ab5dd3a04c5e649c2642c6551652b9`.

Both source programs returned zero. Each revalidated the 79 pinned inputs; independent readback verified all 82 artifact files. The current options-hash context and cached-hash accessor were preserved. No combined compiler checkout, compiler build, Rust tests, native/private-metadata qualification, installation or application timing has occurred.

The six generator-source files, including README.md and QUALIFICATION.md, retain their exact historical pre-execution bytes. This status records the later actual source result without rewriting those frozen documents. Execution and review evidence is in `../../results/hir-options-hash-packed-sidecars-source-01/`.

One qualification wording limitation remains explicit: `Vec::try_reserve_exact` handles its own reservation failure, while decoding and queueing still allocate through `Arc::from` and `BTreeMap::insert`. General out-of-memory recovery is not established. The two 256 MiB policy maps and a temporary 256 MiB input buffer bound serialized payload, not total RSS. Future compiler and lifecycle qualification must retain that distinction.

The nine new session tests, existing compiler/run-make suites, real error and callback/finalization histories, metadata/runtime roles, exporter behavior, and strict Ruff measurement remain future work. Profile spans overlap; this source result establishes no speedup or sub-0.5-second bound.
