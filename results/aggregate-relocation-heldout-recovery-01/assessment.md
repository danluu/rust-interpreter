# Aggregate relocation: complete held-outs

| Case | Paired wall | Paired CPU | Native | Control | Candidate | Gate |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| nushell-type-relations | +1.10% | +1.14% | 7.529s | 4.051s | 4.066s | pass |
| ruff | -0.28% | -0.27% | 5.259s | 2.868s | 2.998s | pass |
| nushell | +1.63% | +2.21% | 0.657s | 0.442s | 0.448s | pass |
| forward-anchored-tls | +2.71% | +1.99% | 1.510s | 0.969s | 1.005s | pass |
| pgrust-sha1-inline8 | +0.35% | +0.23% | 0.810s | 0.635s | 0.638s | pass |
| pgrust | -0.00% | -0.27% | 0.678s | 0.473s | 0.470s | pass |
| rg-aot | +1.61% | +1.94% | 0.564s | 0.186s | 0.191s | pass |

All 588 commands, 105 real-edit pairs and 294 artifacts verify. Each case keeps its own fixed 5% wall and CPU guards. The original Ruff disk-guard stop remains preserved and excluded; the distinct complete retry supplies its fifteen pairs. Source restoration, original assertions and wrong-edit checks remain mandatory. Three cycles on a shared host are descriptive. Target-cache-cold setup is separate; these selected workflows do not establish full-suite support. Private results contain aggregate measurements only.

All held-out guards pass.
