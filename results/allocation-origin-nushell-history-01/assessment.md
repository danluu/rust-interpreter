The extra literal originates in compiler-provided allocation identity before exporter layout. All four origin queries reproduce, all three original reference spans remain present, and all four traced artifacts match their historical counterparts byte-for-byte.

| State | Literal allocations | Creation/widen pointer | Deduplicates-test pointer |
| --- | ---: | ---: | ---: |
| Original | 1 | 224 | 224 |
| Wrong relation edit | 1 | 224 | 224 |
| Generic list API | 2 | 224 | 368 |
| Restored original | 2 | 224 | 368 |

The three references are at ty.rs lines 523, 539 and 554. The latter belongs to test_oneof_deduplicates, which calls the changed Type::list API. In the API and restored states it supplies a different compiler AllocId and produces a separate 14-byte read-only materialization with no relocations. The other two references share their own compiler allocation. IDs are local to each compilation; their numeric values are not stable keys. The exporter has preserved the identities it receives. Changing its map iteration order cannot remove this split.

The pinned local rustc source supplies a plausible mechanism: MIR string-literal construction uses allocate_bytes_dedup; saved-allocation decoding uses reserve_and_set_memory_alloc, which assigns an independent ID, and the incremental query cache uses that decoder. The three source paths and hashes are recorded in summary.json at compiler revision cea272fa356e94bd2ee2cadf376630aa0683867a. Mixing cached and recomputed function MIR is consistent with the observed split, but these traces do not directly record rustc cache hits. The next experiment is a small reduction with incremental compilation enabled and disabled.

Do not merge arbitrary read-only allocations by byte contents or use session allocation IDs as cross-build keys. Function reuse needs symbolic relocations and preserved alias relationships. The earlier measured ~71-ms lowering interval within ~5.3-second warm commands also limits the potential payoff of lowering reuse for this particular workflow.
