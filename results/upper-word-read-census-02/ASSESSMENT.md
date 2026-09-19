# Masked integer consumers add limited coverage

Eight typed controls pass in both profiles, including3,800 comparisons against
the actual binary() helper under poisoned high bits, and signed-source checks.
Six exact machine-traffic controls pass. All earlier eligible registers remain
eligible. Both saved native captures and all original samples reconcile.

The expanded proof covers22,637/26,937 upper stores and33/1,933 block samples /
13/1,429 exhaustive samples (1.71%/0.91%). Most eligible samples remain in flush
spans. This does not justify a standalone runtime omission or timing run.
No production change, guest execution or code publication occurred.

Defer consumer-only omission. Next examine a materially broader representation:
implicit zero high words for whole-function proven narrow values, with native
reads synthesizing zero and interpreter boundaries restoring the logical value.
That proposal must never simply drop upper stores while leaving full-width reads
unchanged. First census actual stores/loads covered by the existing width proof
and bound the repair work using current exact interpreted-PC counts. Count all
narrow interpreted operands as a conservative repair upper bound, including
those already masked, and keep it distinct from measured runtime. Unqualified
representation, ABI and boundary costs still block any implementation decision.
