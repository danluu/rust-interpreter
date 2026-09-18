# Candidate and scope

3081569232 uses custom VM5fd0c1c7 with unchanged adopted exporter cf4b3499 and
wrapper45bca4f2. It extends bounded confined scalar Calls to <=64-byte results /
<=1 KiB frames through a private aggregate buffer and complete prechecked commit.
Original full Rust checking precedes execution. Scalar Calls remain explicit.

Seven complete-VM boundary controls,374 bytecode tests/profile,637 workspace
tests/profile,407 Python passes/22 skips,121 strict/cache commands and three
original profiles qualify this candidate. The exact real-function census retains
32 memory/native-eligible wider bodies. Synthetic/static/profile coverage does
not establish performance. Use the exhaustive-only protocol in SCREEN.md and
the subsequent full regression gates in the previously declared native plan.
