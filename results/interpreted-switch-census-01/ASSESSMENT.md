The saved parser profile executes 64,879 switches with at least 32 cases. Its
linear-search comparison upper bound is 11,655,317; actual comparisons are not
recorded. The largest is reduce_cold PC193: 692 unsorted unique cases, executed
9,022 times, maximum key 2456. The scanner has 72 unsorted unique cases and
29,320 executions. Six host search samples in the independent parser window
make a bounded indexed lookup worth one correctness-qualified primary screen.

The two token cases and folded case execute no such switches. This mechanism
therefore gets a full-parser changed-source primary; token cannot establish its
benefit. These are dynamic opcode counts, not measured values or timing gains.
Use a general bounded cache with dense or sorted indices, retain duplicate-first
semantics and the linear fallback, and keep adoption conditional on the existing
end-to-end gates. No frame initialization changes are included.
