# token-phrase: ordinary versus enlarged MIR inlining

Predeclared gate **fails**. Ordinary/enlarged paired wall ratio 1.068756; CPU ratio 1.070399. Medians: ordinary 4.635s, enlarged 4.334s, native 2.004s.

63 primary commands, 21 Cargo-check controls, 15 edited pairs and 42 artifact hashes verified. Historical harness labels are baseline=ordinary and candidate=enlarged.

Compiler settings change artifacts, lowering, frame layout and instruction count. Original native/assertion controls pass; artifact semantic equivalence is not formally proven. Three cycles are descriptive, not independent statistical trials.
