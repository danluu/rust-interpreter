The isolated candidate pairs register spills into AArch64 STP only for slots 0–31 and 2048 or above. Middle slots retain their two unsigned-offset stores. No VM transition or guest-memory behavior changes. All 173 bytecode tests pass, including 432 hardware value/address/neighbor/ABI cases. The exporter binary is identical to retained6bf.

| Runtime filter | Wins | Paired elapsed change | Paired CPU change |
|---|---:|---:|---:|
| token-phrase | 5/6 | -45.19 ms | -45.73 ms |
| folded | 1/6 | +28.28 ms | +28.71 ms |
| sha1 | 4/6 | -1.71 ms | -1.41 ms |
| tls | 0/6 | +2.37 ms | +2.63 ms |
| pgrust-interpreter | 2/6 | +0.86 ms | +0.73 ms |

This filter uses saved original artifacts; it excludes fresh exports and compilation. Folded and TLS regress despite the predicted code-size reduction. The pgrust interpreter control also varies. No control value is subtracted from JIT timings.

The folded artifact produces exactly 70,452 fewer native bytes, matching the typed prediction. Its complete logical trace is unchanged. The production-RNG token profiles differ in 20 functions, so no exact token-trace claim is made. Original assertions pass in every run. The predicted 462 million fewer weighted machine instructions do not imply a runtime saving or reduced hardware memory traffic.

The 2 completed real-edit workflows win **4/10 commands against retained** and **0/10 against native**. All original tests and wrong-edit controls are preserved; every fresh artifact matches retained and source pins are restored.

| Workflow | Parent wins | Paired command / execution / Cargo change | Native wins | Cold native / parent / candidate |
|---|---:|---|---:|---|
| token-phrase | 2/5 | +27.0 / +1.3 / +40.8 ms | 0/5 | 7.297 / 11.177 / 11.271 s |
| folded-literal-trie | 2/5 | +25.4 / -4.2 / +18.7 ms | 0/5 | 6.672 / 6.978 / 6.984 s |

Paired stage medians need not sum to the command median. All samples, including regressions, remain in the underlying reports.

The candidate is parked without integration: both workflows regress in paired command time, and only4/10 commands improve. Broad native/TLS/fre qualification and binary reproduction have not been run for this candidate. Whole applications, general OS/FFI, guest threads and unwinding remain unsupported.
