The current compiler integration passes 513 workspace Rust tests in each of
debug and release, six component-boundary checks, and 328 Python contracts
(16 declared skips). Five Rust tests remain ignored in each ordinary test run:
the previous three plus two explicit compiler-control tests.

The composed tool is `35df4077b5cfb466cf1a7155374abb867fb8fadeb4f5dbedffe766d5b3621bc1`.
Its VM bytes exactly match the measured guarded-local-facts runtime. Every one
of the previous 125 VM/shared source inputs matches; two new hash-pinned files
form a separate Cargo integration test target, verified from retained metadata.
The exporter and wrapper are newly built and have their own identities. The new
compiler trap paths preserve macro-scope source remapping separately from
compiler-diagnostic remapping. The test harness now has an explicit stock-rustc
codegen setting while retaining its custom-compiler default.

This is build and source compatibility evidence. The two ignored remapping
controls, 119 strict/cache/Cargo commands, 40 real-project edit-history commands
and complete original 114-test parser remain required before publication. The
726 completed timing commands are not repeated; their complete-command ratios
belong to their original compiler binaries and recorded options.
