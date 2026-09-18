# Qualification stopped on an overly specific diagnostic assertion

The first debug command finished with 376 bytecode tests passed and one failed
(13 ignored). The conditional-demand mode test expected the demand diagnostic
from an interpreter invocation that also requested resumable calls. Existing
resumable-mode admission correctly rejected that configuration earlier with its
own diagnostic. No guest bypass or conditional-policy execution failure was
observed. The boundary and prepared-owner controls passed.

The test will disable resumable calls on its interpreter arm so it reaches the
specific demand-mode admission being tested. Retain these original logs and
closure; run the complete qualification under a fresh ID. Release, Python,
packaging and capture commands were not started, and no tool was installed.

[Closed evidence](closure.json), [summary](summary.json).
