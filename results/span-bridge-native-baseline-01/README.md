# Stock-span real bridge baseline

The frozen `63f70679` runner compiled the unchanged `c964a9e0` bridge fixture
with the installed Cmono58 compiler and its actual native standard library,
then passed all four tests in one unfiltered serial harness process. Native
compilation and the harness both returned zero; no test was ignored or filtered.
The span-store patch was not applied. This is correctness evidence for the
existing stock bridge fixture, with no performance or patched-store claim.

Compiler key: `f9fb3e5f59b8567fffd32c936a9864d0baee77038574236710fbcec75a57d33f`.
Compiler source: `58e1e1f5311f4424ea81def4763081f6da62d9b3`.
Native test executable SHA256:
`2dd260e717dabea8455aeddbe00d9933a3889d59a81384ba4659bd063be185fe`.
The original span patch remains
`05aeea42bf6e3cd3aa9c1ec3adfdad65e6846e11e0419dca5490b253c4a922ff`.

The actual controls cover growing/interleaved span handles and reverse reads,
stale same-thread rejection before server dispatch, exact token-stream drop
order, nested execution and panic recovery. The fixture exercises ordinary
same-thread and forced cross-thread strategies internally where appropriate.
The compiler's original internal-feature warning and all intentional panic
stderr remain unmodified in the archive.

The four prepared Python runner-boundary tests passed before native execution.
An earlier setup attempt bound `/usr/bin/python3`, the macOS launcher, instead
of the actual Xcode interpreter. Its guard rejected the mismatch before any test
child started. The failed attempt is retained; a fresh attempt changed the setup
plan's interpreter identity and owned run paths, with fixture and reviewed baseline driver source
unchanged. It then passed all four Python controls. No unrelated process was
controlled and no source, compiler or cache was replaced to obtain these results.

Native supervisor/helper PIDs were 41632/41636; rustc was 41639 and the test
harness 41647. The canonical workload lock covered native admission at
1789327372.392203 through completion at 1789327374.0334852. Raw timing fields
are process receipts, not optimization measurements.

`summary.json` records exact outcomes, keys, archive identity and the retained
failure. `evidence.tar.gz` contains raw command/supervisor output, complete
installed compiler readiness proof, exact source and helper snapshots, stock
bridge source files, plans, dep-info and artifact hashes. It excludes the test
executable and all compiler binaries/caches; the generated executable remains
in the owned work directory with its recorded hash. Every archived member was
read back and compared to its original bytes under the canonical lock.

This run does not qualify the proposed span store or the separate full
compiler-server/dylib/caller matrix. Those future checks remain distinct from
this completed baseline fixture qualification.
