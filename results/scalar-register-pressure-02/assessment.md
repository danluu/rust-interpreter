# Spill category partition invalidated

The two structural controls and all 245 exact native-body reconstructions pass,
and the pool totals reproduce census01. A subsequent source review found that
the new category partition counted operands of dead IR nodes. Its categories
do not sum to the live-only pool totals, so do not use this partition to choose
an implementation. The frozen output is retained, not rewritten. Correct the
liveness filter, add a dead-use regression and require partition reconciliation
in a fresh census. The earlier local-pool conclusion remains unchanged.
