# Reconstruct small-memory costs in fresh scalar captures

Fresh current-VM samples show Copy spans at 487/1,814 and 290/1,480 generated
self samples, versus 57 and 123 in private scalar bodies. Classify the Copy
spans before changing production emission. Old scratch-forwarding and general
address-check candidates remain parked; no unchanged timing retry is planned.

Extend only the existing test-only small-memory observer to accept schema 2.
Rebuild immutable scalar entry metadata at each saved arena offset/base, verify
every scalar body's bytes, then reconstruct every ordinary function twice with
observation off/on. Require exact words, spans, assertions and resume identities.
No Code allocation, executable publication or guest execution is permitted.
Scalar spans retain whole-body identity and do not become small-memory spans.

Run the four focused memory partition controls (including saved scalar targets
at two arena bases), two fine-attribution controls and two saved real captures.
Use the existing fixed shared target, same source root, two Cargo workers, the
14 GiB / max(8 GiB + twice allocated target) admission and 8 GiB child floor.
Keep the global benchmark lock, exact command receipts and source/artifact
bindings. This is an offline diagnostic, not a production runtime change.

Join only captured self PCs to exact source-labeled memory subparts. Preserve
ambiguity explicitly. The old exact profile supplies static operation names
only. Do not turn static words or partial sample shares into retired instruction
counts, whole-command timing, expected gains or revised end-to-end gates.
