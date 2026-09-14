# Complete arbitrary-register retention inventory

The corrected representation counts every production liveness query. Captured
ordinary-function sets retain 11,820,122 bytes for token block, 14,798,244 for
token exhaustive and 2,150,945 for folded. These replace the incomplete
7.7/9.7/1.3 MB estimates. The counts include compact live words/indices,
exceptional successors, pair masks, sorted hints and other analysis payload.

Across all validated functions, payload totals are 51,042,449 bytes for token
(5,468 functions), 11,129,275 for folded (1,048) and 40,041,534 for the current
parser (11,832). All-function totals are not simultaneous ownership: the runtime
admits reached plans into a 16 MiB pool and otherwise falls back to eager emission.
The captured subsets also do not establish future encounter order or admissions.

One inventory control per profile and three saved-artifact observers pass in
3.99 seconds. Every function's enumerated capacities equal its checked retention
charge. The closure binds all sources, inputs and reports. No guest or native
code ran in this inventory. Counts exclude allocator rounding, transient work,
pool indexing, separate publication metadata and code. The test layout includes
an extra oracle header, while its full graph buffers are reported separately.
These are capacity counts, not RSS or speedups.
