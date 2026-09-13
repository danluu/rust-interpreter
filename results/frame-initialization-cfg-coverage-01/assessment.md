The first bounded CFG/interprocedural proof covers zero of the 110 block and
100 exhaustive frame-clearing samples. It admits 1,629,854 / 1,152,565 native
calls; the callee-effect summary adds only 43 eligible calls in each profile.
This is insufficient sampled scope for runtime clear removal. Preserve the
result and the unchanged runtime.

Eight controls pass in both profiles, including a 6,400-case independent byte
oracle. The analyzer examines 5,468 functions, proves 342 confined, and admits
630 initializations without callee summaries versus 635 with them. It uses under
7 million of the 256 million work units in each initialization phase. Build
setup takes 8.73 seconds; analysis about 1.65 seconds. No guest code executes.
The first standalone compile failure was a missing unchanged register-init
helper; it ran zero tests. Its source, output and terminal remain verified.

The exact clearing-sample join and native call totals are reconciled. The
coverage audit binds both build histories to their own Git sources and checks
all current saved inputs. Counts and sample proportions have different scopes;
alignment padding and proposed runtime address guards remain additional costs.

A subsequent read-only decline review found explicit constant-length FillBytes
initialization in several sampled helpers, and an is_aligned_to local load
addressed by Local plus a constant eight-byte offset. The first proof treats
these as unknown. Extend only the typed constant/local facts and exact constant
memory extents, with new alias/truncation/join tests. The rendered snippets
motivate that diagnostic; they establish no safety proof or performance gain.
