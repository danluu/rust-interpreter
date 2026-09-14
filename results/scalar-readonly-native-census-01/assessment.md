The corrected native prototype admits 392 read-only functions at 409 direct
callsites. Both profile modes emit successfully under the existing scalar
limits. The actual Call proof policy uses 3,987,765 of 256 million work units.
All 71 distinct previously captured scalar bodies re-emit byte-for-byte:
60 in block and 69 in exhaustive, with overlap between captures.

New native candidates cover 42 transition samples and 52 body samples in the
block capture, including nine frame-clear samples. Exhaustive has no coverage.
This preserves nearly all the reference model's observed scope, but does not
measure dynamic preparation, shared-arena admission, execution speed or complete
command time. The sampled windows remain partial and perturbed.

The closure verifies 331 source/retained bindings and 15 artifacts against
`d394fdf1`. No original-project guest runs and no native code is published by
the census. The separate corrected control history passes 359 bytecode tests
per profile. The initial passing 358-test history and its uncovered heap-free
ABI issue remain explicit; the corrected emitter uses the actual heap mode.

Proceed to an immutable candidate build, strict/cache checks and exact original
profiles against the adopted scratch/scalar tool. Both comparison arms must
enable scalar Calls. Then use a fresh primary-first changed-source screen;
all full-project and parser adoption gates remain required. Main and existing
installed tools retain the adopted runtime until qualification succeeds.
