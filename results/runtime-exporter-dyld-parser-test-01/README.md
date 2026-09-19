# Delayed-load parser controls

All 24 tests passed in one ordinary run, including both complete saved streams
from the [failed metadata attempt](../runtime-exporter07-metadata-failure-01/STATUS.md).
The original failure and all raw output remain preserved.

The parser retains every byte, UUID, process ID and transition. A transition
must name one previously loaded image and match its current state. Unknown
messages, ambiguous names, foreign processes and an inactive compiler driver
are rejected. Both transition directions follow
[Apple's dyld implementation](https://github.com/apple-oss-distributions/dyld/blob/main/dyld/DyldRuntimeState.cpp).

These are saved-data and parser checks. They ran no compiler probes or builds
and do not establish metadata, application or performance qualification.
