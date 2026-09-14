# Compact the liveness retained for native emission

Keep the original bounded full-CFG liveness and register ranking. After selecting
at most three persistent registers, project their live-in bits into one u8 per
PC; functions with no assignments retain no mask buffer. Native continuation
spills consult these bits by assigned index. The full graph is then dropped in
production. Existing offline diagnostics retain an explicitly cfg(test) oracle.

Extend the independent path-search control over 200 seeded CFGs to compare
selected masks at every PC. Preserve out-of-range/one-past-code behavior and
empty assignment handling. Run all 350 bytecode controls in both profiles and
reassemble the two exact adopted captures, then repeat the saved storage inventory
with the compact representation. Report test-only oracle buffers separately;
the inventory's inline header uses the test layout and overstates production.

No demand policy, live patching or adoption. This removes retained production
storage, but adds a bounded projection step and does not avoid full analysis.
Only original changed-source comparisons can establish a latency improvement.
