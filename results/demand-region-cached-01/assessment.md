# Cached plans and compact fragment metadata qualify

Source f117390d passed 349 bytecode controls in each of debug and release
(12 observers ignored per profile), then reconstructed both adopted unprofiled
captures and independently reassembled all 20,033 block-test and 23,406
exhaustive-test regions. All 11,313,812 / 13,757,056 bytes, assertion identities,
operation spans, entries and declared successor relocations matched exactly.
Every fragment uses one entry/resume/internal slot keyed by its selected PC.
Repeated out-of-order guarded-region staging is stable; accidental use of the
whole-function publisher fails before any code or metadata publication.

Four commands took 65.607546 seconds of setup/qualification time. The exact
closure verifies 292 source/input bindings and ten output artifacts. No original
project guest command ran and the saved observers published no executable code.
The native unit controls do execute their synthetic generated-code fixtures.

Guard plans now consume their shared work budget once in original source order;
selection binary-searches the cached leaders without rescanning earlier bodies.
Eager emission still produces the same code, but can analyze more of a function
before a later code-size refusal. Retaining analysis also has a storage cost.
Measure and bound that cost next; this is not an end-to-end performance result
or adoption of demand execution. The runtime prototype remains on its branch.
