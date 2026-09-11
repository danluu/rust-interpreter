# Build experiment dev-profiles-03

Seconds; cold has one observation per variant. Warm entries are medians, with observed min–max. These are local development builds on a shared host, not production performance claims.

| Project | Backend | Case | n | Build median | Min–max | Feedback median | Cache hits / misses |
|---|---|---|---:|---:|---:|---:|---:|
| fre | clif | body-edit | 5 | 1.211 | 1.184–1.250 | 1.646 | 0 / 0 |
| fre | clif | cold | 1 | 8.073 | 8.073–8.073 | 8.657 | 0 / 0 |
| fre | clif | no-op | 6 | 0.092 | 0.090–0.102 | 0.463 | 0 / 0 |
| fre | clif | revert | 5 | 1.217 | 1.162–1.292 | 1.658 | 0 / 0 |
| fre | clif-cache | body-edit | 5 | 1.220 | 1.170–1.318 | 1.691 | 1185 / 5 |
| fre | clif-cache | cold | 1 | 9.563 | 9.563–9.563 | 10.210 | 25664 / 17266 |
| fre | clif-cache | no-op | 6 | 0.096 | 0.091–0.100 | 0.483 | 0 / 0 |
| fre | clif-cache | revert | 5 | 1.223 | 1.172–1.271 | 1.645 | 1190 / 0 |
| fre | llvm | body-edit | 5 | 1.224 | 1.176–1.227 | 1.619 | 0 / 0 |
| fre | llvm | cold | 1 | 8.934 | 8.934–8.934 | 9.373 | 0 / 0 |
| fre | llvm | no-op | 6 | 0.093 | 0.089–0.098 | 0.415 | 0 / 0 |
| fre | llvm | revert | 5 | 1.190 | 1.181–1.242 | 1.573 | 0 / 0 |
| nushell | clif | body-edit | 5 | 1.355 | 1.124–2.651 | 6.412 | 0 / 0 |
| nushell | clif | cold | 1 | 73.989 | 73.989–73.989 | 79.689 | 0 / 0 |
| nushell | clif | no-op | 6 | 0.323 | 0.300–0.694 | 5.540 | 0 / 0 |
| nushell | clif | revert | 5 | 1.183 | 1.133–3.104 | 6.346 | 0 / 0 |
| nushell | clif-cache | body-edit | 5 | 1.174 | 1.158–3.467 | 6.883 | 110 / 5 |
| nushell | clif-cache | cold | 1 | 79.660 | 79.660–79.660 | 84.842 | 152189 / 40458 |
| nushell | clif-cache | no-op | 6 | 0.316 | 0.302–0.751 | 5.540 | 0 / 0 |
| nushell | clif-cache | revert | 5 | 1.185 | 1.121–1.758 | 6.716 | 115 / 0 |
| nushell | llvm | body-edit | 5 | 1.182 | 1.073–2.457 | 5.473 | 0 / 0 |
| nushell | llvm | cold | 1 | 90.974 | 90.974–90.974 | 95.056 | 0 / 0 |
| nushell | llvm | no-op | 6 | 0.339 | 0.306–0.898 | 4.495 | 0 / 0 |
| nushell | llvm | revert | 5 | 1.157 | 1.118–2.648 | 5.424 | 0 / 0 |
| pgrust | clif | body-edit | 5 | 1.573 | 1.335–3.012 | 6.602 | 0 / 0 |
| pgrust | clif | cold | 1 | 95.599 | 95.599–95.599 | 100.770 | 0 / 0 |
| pgrust | clif | no-op | 6 | 0.645 | 0.594–0.873 | 5.367 | 0 / 0 |
| pgrust | clif | revert | 5 | 1.399 | 1.327–2.738 | 5.985 | 0 / 0 |
| pgrust | clif-cache | body-edit | 5 | 1.438 | 1.307–2.658 | 6.126 | 45 / 5 |
| pgrust | clif-cache | cold | 1 | 105.975 | 105.975–105.975 | 110.805 | 290394 / 62797 |
| pgrust | clif-cache | no-op | 6 | 0.619 | 0.600–1.075 | 5.387 | 0 / 0 |
| pgrust | clif-cache | revert | 5 | 1.368 | 1.332–2.776 | 6.217 | 50 / 0 |
| pgrust | llvm | body-edit | 5 | 1.677 | 1.242–2.673 | 5.067 | 0 / 0 |
| pgrust | llvm | cold | 1 | 106.581 | 106.581–106.581 | 109.732 | 0 / 0 |
| pgrust | llvm | no-op | 6 | 0.663 | 0.598–1.183 | 4.141 | 0 / 0 |
| pgrust | llvm | revert | 5 | 1.289 | 1.247–1.817 | 4.820 | 0 / 0 |
| rg-aot | clif | body-edit | 5 | 0.203 | 0.199–0.204 | 0.553 | 0 / 0 |
| rg-aot | clif | cold | 1 | 3.513 | 3.513–3.513 | 3.987 | 0 / 0 |
| rg-aot | clif | no-op | 6 | 0.076 | 0.069–0.082 | 0.325 | 0 / 0 |
| rg-aot | clif | revert | 5 | 0.202 | 0.193–0.212 | 0.555 | 0 / 0 |
| rg-aot | clif-cache | body-edit | 5 | 0.198 | 0.189–0.205 | 0.550 | 35 / 5 |
| rg-aot | clif-cache | cold | 1 | 3.730 | 3.730–3.730 | 4.067 | 538 / 1017 |
| rg-aot | clif-cache | no-op | 6 | 0.075 | 0.069–0.083 | 0.330 | 0 / 0 |
| rg-aot | clif-cache | revert | 5 | 0.202 | 0.194–0.226 | 0.543 | 40 / 0 |
| rg-aot | llvm | body-edit | 5 | 0.199 | 0.194–0.204 | 0.500 | 0 / 0 |
| rg-aot | llvm | cold | 1 | 3.600 | 3.600–3.600 | 3.905 | 0 / 0 |
| rg-aot | llvm | no-op | 6 | 0.081 | 0.067–0.082 | 0.283 | 0 / 0 |
| rg-aot | llvm | revert | 5 | 0.202 | 0.190–0.204 | 0.489 | 0 / 0 |
| ruff | clif | body-edit | 5 | 0.705 | 0.571–1.350 | 4.476 | 0 / 0 |
| ruff | clif | cold | 1 | 44.818 | 44.818–44.818 | 48.411 | 0 / 0 |
| ruff | clif | no-op | 6 | 0.207 | 0.194–0.303 | 3.501 | 0 / 0 |
| ruff | clif | revert | 5 | 0.628 | 0.570–1.136 | 4.366 | 0 / 0 |
| ruff | clif-cache | body-edit | 5 | 0.715 | 0.562–1.320 | 4.429 | 200 / 5 |
| ruff | clif-cache | cold | 1 | 50.522 | 50.522–50.522 | 54.305 | 204494 / 36710 |
| ruff | clif-cache | no-op | 6 | 0.209 | 0.190–0.418 | 3.782 | 0 / 0 |
| ruff | clif-cache | revert | 5 | 0.691 | 0.570–1.229 | 4.156 | 205 / 0 |
| ruff | llvm | body-edit | 5 | 0.483 | 0.433–1.213 | 1.595 | 0 / 0 |
| ruff | llvm | cold | 1 | 70.757 | 70.757–70.757 | 71.776 | 0 / 0 |
| ruff | llvm | no-op | 6 | 0.211 | 0.187–0.290 | 1.250 | 0 / 0 |
| ruff | llvm | revert | 5 | 0.439 | 0.430–1.054 | 1.689 | 0 / 0 |
