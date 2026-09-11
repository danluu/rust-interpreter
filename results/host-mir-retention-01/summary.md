# Native host MIR retention experiment

The candidate remains isolated. It reduces native host metadata, but its first
Nushell production-edit comparison wins only 2/5 pairs against retained and
regresses by a paired 219.4 ms. Cold build-and-test time is 65.502 s versus
67.662 s retained and 78.991 s native. The lower cold time does not establish a
repeatable gain or satisfy the edited-command objective.

| Measurement | Native | Retained | Candidate |
| --- | ---: | ---: | ---: |
| Median edited command | 10.118 s | 6.189 s | 6.408 s |
| Cold command | 78.991 s | 67.662 s | 65.502 s |

The wrapper leaves native host libraries on ordinary rustc MIR-retention policy
when a separate guest MIR sysroot and explicit guest target distinguish them.
It retains normal checking, native build scripts and macros, user flags, and
forced guest MIR retention. The custom interpreter and direct AArch64 emitter
are byte-for-byte the retained VM.

The final native host nu-protocol metadata shrinks from 15,882,938 to 12,608,410
logical bytes (20.6%). Ordinary guest metadata stays the same size, though its
hash differs. All seven executed guest artifact pairs match byte for byte,
including cold and deliberately incorrect edits. These file sizes describe this
unit after the final edit; they are not physical disk allocation or time savings.

Validation passes 165 bytecode tests, seven exporter tests, and 16 checks of the
actual wrapper's forwarded arguments using a recording rustc. The real workflow
preserves the original tests and source pin, exports fresh artifacts, runs fresh
native controls, and rejects the deliberately wrong edit in every mode. The
build harness incorrectly expected nine exporter tests; the preserved logs show
three existing tests plus four new tests all passed. Its count guard was audited
without rerunning or weakening any test assertion.

Per-edit candidate-minus-retained command differences are −35.6, +219.4, +525.1,
−1372.7 and +1567.6 ms. Their large swings resemble the earlier scalar-promotion
runs despite this separate implementation and identical guest code. The next
measurement uses the same retained tool in both custom slots, with independent
caches and the same real source edits. This control can reveal variation present
without a compiler change. It does not replace or discard the original results.

[Complete comparison](../paired-host-mir-retention-corpus-nushell-type-relations-01/summary.md).
Evidence hashes and the isolated source are indexed in [summary.json](summary.json).

The subsequent [identical-tool control](../identical-tool-control-01/summary.md) reproduces large warm-command swings with no implementation difference: +181 ms median slot difference and up to 1.68 s per edit. This limits attribution of the earlier Nushell timing differences. It is not valid to subtract the separate control as a correction or to conclude that either candidate has zero effect. Both remain isolated while a consecutive-edit protocol is evaluated.
