# Oxc interpreter/JIT compatibility

The fixed Oxc plugin-normalization case passed its complete interpreter and JIT history through the ordinary launcher. All three unchanged tests passed on the original source, after each of the three production refactors, and after restoration. Each test was also run individually against the wrong-prefix negative in both engines; all six negatives reached the expected guest assertions. Every artifact reported zero unavailable call sites.

This qualifies this test case for subsequent runtime/compiler experiments. It does not meet the 0.5-second build target and is not a repeated performance benchmark. The selected library-test crate was freshly compiled on every call; no no-change cache hit is presented as an edit result.

The upstream revision remains `4d5c812d6b16c23fa71d106cf87f7f20ddee69b1`. Source states and test selections match the [clean native history](../oxc-native-compatibility-02/README.md). Profiles and default features were unchanged. The runtime source and registry inputs came from the [qualified source transfer](../oxc-runtime-source-acquisition-01/README.md).

The run used the published runtime compiler `eca3d1317ba4c852d64de435aa0f0e5d87ae63bd4eb96cfafacc7b0a85841d03`, tool composition `7610e295912b132303c95db6a587f9288c03a7f84b691de8ea60093e2829622a`, and shared standard library `e4d1cd29bf4dbac5f9cbf6a92c77a562b89f7079c4474653f180346a00f24b63`. The exact successful publication receipt, copied tool identities, 23 publication children and installed-tool reader are bound in the retained freeze.

Both engines used MIR optimization level 3 with HIR body capture/reuse disabled and function/borrow-check caches off. JIT used resumable calls and persistent registers. The launcher used `--trap-unsupported-calls --run-try-callbacks`, an instruction limit of 1,000,000,000 and an allocation limit of 150,000. Zero unavailable sites in this case does not establish general Rust support or qualify untested application paths.

These are single-history diagnostic build-to-ready observations, in seconds; the two engines used separate fresh caches. Build-to-ready includes launcher/Cargo preparation and selected-bytecode verification and excludes VM startup/execution. Different qualified compiler toolchains were used for the native and runtime histories, so these observations are not a controlled native/runtime speedup measurement.

| Source state | Interpreter | JIT |
| --- | ---: | ---: |
| Original, cold | 48.963 | 46.832 |
| Production edit 1 | 5.878 | 5.715 |
| Production edit 2 | 5.728 | 5.953 |
| Production edit 3 | 5.876 | 5.848 |
| Restored original | 5.967 | 5.746 |

The six individual negative builds took 5.549–5.972 seconds to become ready. Guest execution for successful edited/restored batches took 3.95–8.36 milliseconds. These observations identify substantial remaining build work; no timing distribution or sub-0.5-second result is claimed.

The complete 16-call history ran under the canonical lock with a 600-second admission bound and unchanged 24/9/8 GiB entry/stop/floor gates. It admitted with 28,011,720,704 free bytes and finished with 25,072,775,168. Recorded allocation was 2,877,333,504 bytes of cache and 115,138,560 bytes of evidence. The source was restored, and final runtime, standard-library, tool, provider, source and all 323 registry-package byte checks passed. No strip or loader failure was reported.

`evidence.tar.gz` retains all 16 raw launcher receipts and outputs, actual compiler argument records, each selected bytecode artifact and sidecars, source-state proofs, all 232 frozen inputs, exact plan/launch and outer supervisor records, and the independent verifier/result. Cache and temporary payloads remain in the recorded owner. Extraction recreates paths relative to the experiment worktree; absolute paths inside records describe the original execution environment.

- Terminal receipt SHA-256: `32e79739d158fc356ea7bb0773c162a035b3faade3ca2e78ae9a240352d68e74`.
- Independent verification SHA-256: `e0104be6135fc537e8dca0047483b7b4b8bb78ed66ba344cd1dfa87a39180143`.
- Archive: 856 regular members, 110,764,871 uncompressed bytes, 32,065,808 compressed bytes; SHA-256 `343d036cb6bc31d67d9200d97a21774d3431c1fb4c9c87daa1e6d4a5d57a4a95`.
- Manifest SHA-256: `670239bb956886af516eb5f9bf4f4c797d6f3fe26504ce9bf75b0a944385cabb`.

The independent audit reconciled every frozen live/retained input, exact child argv/environment/cwd/raw hashes and parent/time interval, selected bytecode/catalog/call report, recorded compiler route and flags, all negative assertions and source restoration. Archive verification checked every member hash and consumed the full gzip stream through CRC/EOF.
