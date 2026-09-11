# Build experiment native-repository-04

Seconds; cold has one observation per variant. Warm entries are medians, with observed min–max. These are local development builds on a shared host, not production performance claims.

| Project | Backend | Case | n | Build median | Min–max | Feedback median | Cache hits / misses |
|---|---|---|---:|---:|---:|---:|---:|
| pgrust | llvm | body-edit | 3 | 1.752 | 1.522–1.841 | 4.707 | 0 / 0 |
| pgrust | llvm | cold | 1 | 81.138 | 81.138–81.138 | 84.176 | 0 / 0 |
| pgrust | llvm | no-op | 4 | 0.669 | 0.645–0.900 | 3.519 | 0 / 0 |
| pgrust | llvm | revert | 3 | 1.183 | 1.130–2.283 | 4.543 | 0 / 0 |
| pgrust | llvm-unwind | body-edit | 3 | 1.201 | 1.186–1.823 | 4.888 | 0 / 0 |
| pgrust | llvm-unwind | cold | 1 | 88.183 | 88.183–88.183 | 91.509 | 0 / 0 |
| pgrust | llvm-unwind | no-op | 4 | 0.818 | 0.626–1.017 | 4.357 | 0 / 0 |
| pgrust | llvm-unwind | revert | 3 | 1.265 | 1.157–1.636 | 4.637 | 0 / 0 |
