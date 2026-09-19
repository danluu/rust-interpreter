# Options-hash candidate compiler build

The compiler candidate `4de35bdacef0e3cd18a66bc30b5459c19e09b118`
completed all eight planned build and observation stages. It passed 27 lowering
tests, 18 interface tests, and 15 run-make-support unit tests. The support crate's
doctests produced one pass and two source-declared ignored cases. The actual
native compiler reports LLVM 23.1.1 and the expected candidate source identity.

The change caches the immutable session-options dependency hash in the compiler
context. This result qualifies its compiler build and direct crate tests. It
does not establish an application speedup, the 0.5-second target, native run-make
correctness, beta-sysroot composition, or the serial/concurrent hash-driver
checks; those stages require their own actual results.

The retained history contains 26 actual compiler-stage commands and 25 successful
logical commands across three controllers. The first controller completed 16
commands, including all 27 lowering tests, before rejecting three incorrectly
derived test names. The next controller completed the native build and interface
tests, then failed because run-make-support has no bootstrap `build` rule. The
final continuation ran its registered `test` rule and the two remaining Git
checks. Completed compiler commands were not rerun to repair those controller
errors. All original failures and raw output remain separate.

The archive also preserves the 13 monitor controls and seven support-route
controls, an earlier pre-admission environment failure, and the support-control
launcher attempt whose exit was not observed and which produced no admission
evidence. Fifteen fast compiler-stage child observations lack a contemporaneous
working-directory probe; their recorded launch directories and observed process
identities remain available. No missing observation is inferred.

Before the final continuation, a separately reviewed transition retired 4,646
single-link compiler intermediate files while preserving the compiler's private
stamp members, installed providers, loader routes, and source bytes. The first
retirement attempt removed one file before a directory-bookkeeping check failed;
its partial audit and the separate successful 4,645-file recovery remain explicit.
The final continuation bound the actual remaining tree after that transition.

The independent final audit reconciled all command owners, arguments,
environments, raw stream hashes and times; rehashed 100,917 immutable inputs
(2,979,878,628 bytes) and 992 final output files (758,408,218 bytes); and verified
the selected SDK, native loader trace and actual support producer. The combined
217 capacity observations remained within the declared limits. These samples
are observations, not a reservation or proof of every instantaneous peak.

`manifest.json` records every logical archive member and its digest, the separate
stage outcomes, and the prior admission archive reference. `evidence.tar.gz`
deduplicates matching contents while retaining each logical path. Archive
qualification rereads every member and the complete gzip stream through EOF/CRC.
The archive excludes live compiler, registry, SDK and installed-provider payloads.
