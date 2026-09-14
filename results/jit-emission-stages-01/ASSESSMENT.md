# Ordinary code emission dominates its preparation stages

Both accounting controls pass in debug and release. All three closed adopted
captures reconstruct byte-for-byte, with identical entries, resumes, assertions
and operation counts. Five commands, no guest execution or native publication.
Closure verifies318 frozen inputs and13 artifacts.

| Offline second-emission interval | Block | Exhaustive | Parser |
| --- | ---: | ---: | ---: |
| All ordinary functions |91.63 ms|113.63 ms|66.15 ms|
| Native regions |50.84 ms|64.24 ms|33.04 ms|
| Register liveness |23.42 ms|28.43 ms|15.97 ms|
| Advisory call slots |7.62 ms|9.12 ms|4.21 ms|
| Native transitions |3.56 ms|4.29 ms|7.54 ms|

These are test-build diagnostic intervals with warm inputs and clock overhead,
not edited-command timings or recoverable latency. Scalar preparation, decoding,
validation and code publication are outside this ordinary-emission measurement.
The observer covers1050/1245/2118 ordinary functions and reconstructs60/69/662
scalar bodies separately. Other stages and unaccounted time remain in summary.

The split does not justify a liveness-only runtime candidate against the current
full-command variation, or remove the known correctness/invalidation barriers to
persistent caching. Keep those options deferred. Return to guest memory work:
the emitter forwards local frame values but does not currently fold a Load/Copy
whose source is explicitly a known address in immutable Program.data. Measure
that narrowly proved scope against saved instruction samples before adding a
runtime path. This uses an actual memory operand and immutable bytes, not guessed
pointer provenance or normalized cache identities.
