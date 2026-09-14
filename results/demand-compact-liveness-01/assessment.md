# Compact assigned liveness preserves native emission

Source 334fda50 passes 350 bytecode controls in each of debug and release
(13 ignored observers per profile), including the independent path-search
comparison of selected live masks over 200 seeded CFGs. The two adopted
captures reconstruct and reassemble exactly: 20,033 / 23,406 regions,
11,313,812 / 13,757,056 bytes, with unchanged spans, entries and assertions.
Four qualification commands take 64.412445 seconds. The closure verifies
300 source/input bindings and ten output artifacts.

Production retains one u8 per PC only when a function has selected persistent
registers. The original bounded full-CFG analysis and ranking still run; their
large buffers are dropped after projection. Existing cfg(test) observers keep
the full graph as a separately identified oracle, while native spill generation
uses the compact mask in both tests and production. No demand execution or
publication behavior changes, and no end-to-end gain is established.
