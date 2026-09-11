# folded-literal-trie: ordinary versus enlarged MIR inlining

Predeclared gate **fails**. Ordinary/enlarged paired wall ratio 1.045500; CPU ratio 1.055560. Medians: ordinary 2.111s, enlarged 2.008s, native 1.685s.

63 primary commands, 21 Cargo-check controls, 15 edited pairs and 42 artifact hashes verified. Historical harness labels are baseline=ordinary and candidate=enlarged.

Compiler settings change artifacts, lowering, frame layout and instruction count. Original native/assertion controls pass; artifact semantic equivalence is not formally proven. Three cycles are descriptive, not independent statistical trials.
