# Build experiment pilot-02

Seconds; cold has one observation per variant. Warm entries are medians, with observed min–max. These are local development builds on a shared host, not production performance claims.

| Project | Backend | Case | n | Build median | Min–max | Feedback median | Cache hits / misses |
|---|---|---|---:|---:|---:|---:|---:|
| nushell | clif | body-edit | 3 | 1.832 | 1.812–2.013 | 6.033 | 0 / 0 |
| nushell | clif | cold | 1 | 67.202 | 67.202–67.202 | 71.477 | 0 / 0 |
| nushell | clif | no-op | 4 | 0.413 | 0.264–0.681 | 4.949 | 0 / 0 |
| nushell | clif | revert | 3 | 1.821 | 1.777–2.071 | 6.236 | 0 / 0 |
| nushell | clif-cache | body-edit | 3 | 1.806 | 1.753–1.816 | 6.392 | 66 / 0 |
| nushell | clif-cache | cold | 1 | 83.421 | 83.421–83.421 | 88.004 | 373635 / 111408 |
| nushell | clif-cache | no-op | 4 | 0.334 | 0.267–0.763 | 4.775 | 0 / 0 |
| nushell | clif-cache | revert | 3 | 1.861 | 1.788–2.008 | 6.297 | 66 / 0 |
| nushell | llvm | body-edit | 3 | 1.583 | 1.572–2.511 | 4.990 | 0 / 0 |
| nushell | llvm | cold | 1 | 74.516 | 74.516–74.516 | 77.983 | 0 / 0 |
| nushell | llvm | no-op | 4 | 0.419 | 0.267–0.727 | 3.734 | 0 / 0 |
| nushell | llvm | revert | 3 | 1.579 | 1.572–2.157 | 5.321 | 0 / 0 |
| pgrust | clif | body-edit | 3 | 2.815 | 2.720–3.233 | 6.593 | 0 / 0 |
| pgrust | clif | cold | 1 | 107.054 | 107.054–107.054 | 110.832 | 0 / 0 |
| pgrust | clif | no-op | 4 | 0.695 | 0.570–1.098 | 4.292 | 0 / 0 |
| pgrust | clif | revert | 3 | 2.169 | 2.032–3.149 | 6.084 | 0 / 0 |
| pgrust | clif-cache | body-edit | 3 | 3.516 | 2.090–4.631 | 7.146 | 27 / 0 |
| pgrust | clif-cache | cold | 1 | 119.160 | 119.160–119.160 | 122.811 | 298678 / 65001 |
| pgrust | clif-cache | no-op | 4 | 0.682 | 0.577–1.132 | 4.580 | 0 / 0 |
| pgrust | clif-cache | revert | 3 | 2.148 | 1.822–2.993 | 5.867 | 27 / 0 |
| pgrust | llvm | body-edit | 3 | 2.048 | 1.905–2.864 | 4.600 | 0 / 0 |
| pgrust | llvm | cold | 1 | 111.351 | 111.351–111.351 | 114.429 | 0 / 0 |
| pgrust | llvm | no-op | 4 | 0.670 | 0.563–0.943 | 3.240 | 0 / 0 |
| pgrust | llvm | revert | 3 | 2.464 | 1.585–2.735 | 5.081 | 0 / 0 |
| rg-aot | clif | body-edit | 3 | 0.203 | 0.201–0.207 | 0.457 | 0 / 0 |
| rg-aot | clif | cold | 1 | 3.226 | 3.226–3.226 | 3.471 | 0 / 0 |
| rg-aot | clif | no-op | 4 | 0.038 | 0.028–0.046 | 0.282 | 0 / 0 |
| rg-aot | clif | revert | 3 | 0.203 | 0.192–0.210 | 0.449 | 0 / 0 |
| rg-aot | clif-cache | body-edit | 3 | 0.196 | 0.175–0.205 | 0.456 | 21 / 0 |
| rg-aot | clif-cache | cold | 1 | 3.345 | 3.345–3.345 | 3.637 | 7793 / 6667 |
| rg-aot | clif-cache | no-op | 4 | 0.040 | 0.029–0.042 | 0.279 | 0 / 0 |
| rg-aot | clif-cache | revert | 3 | 0.204 | 0.188–0.218 | 0.461 | 21 / 0 |
| rg-aot | llvm | body-edit | 3 | 0.191 | 0.178–0.193 | 0.417 | 0 / 0 |
| rg-aot | llvm | cold | 1 | 3.053 | 3.053–3.053 | 3.226 | 0 / 0 |
| rg-aot | llvm | no-op | 4 | 0.033 | 0.029–0.044 | 0.233 | 0 / 0 |
| rg-aot | llvm | revert | 3 | 0.189 | 0.181–0.197 | 0.388 | 0 / 0 |
| ruff | clif | body-edit | 3 | 0.940 | 0.916–1.074 | 3.688 | 0 / 0 |
| ruff | clif | cold | 1 | 43.299 | 43.299–43.299 | 46.157 | 0 / 0 |
| ruff | clif | no-op | 4 | 0.150 | 0.145–0.160 | 2.725 | 0 / 0 |
| ruff | clif | revert | 3 | 0.966 | 0.909–0.969 | 3.427 | 0 / 0 |
| ruff | clif-cache | body-edit | 3 | 0.933 | 0.893–1.051 | 3.580 | 114 / 0 |
| ruff | clif-cache | cold | 1 | 51.393 | 51.393–51.393 | 54.143 | 324826 / 59234 |
| ruff | clif-cache | no-op | 4 | 0.156 | 0.153–0.161 | 2.759 | 0 / 0 |
| ruff | clif-cache | revert | 3 | 0.892 | 0.889–1.017 | 3.499 | 114 / 0 |
| ruff | llvm | body-edit | 3 | 0.519 | 0.494–0.523 | 1.444 | 0 / 0 |
| ruff | llvm | cold | 1 | 68.440 | 68.440–68.440 | 69.448 | 0 / 0 |
| ruff | llvm | no-op | 4 | 0.160 | 0.148–0.189 | 1.016 | 0 / 0 |
| ruff | llvm | revert | 3 | 0.505 | 0.498–0.569 | 1.437 | 0 / 0 |

Failed configurations are excluded from timing comparisons:

- fre / llvm: build-failed
- fre / clif-cache: build-failed
- fre / clif: build-failed
