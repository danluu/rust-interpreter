# Scratch-memory qualification on the scalar Call base

The candidate reuses x9 for exact eight-byte local Loads and Copies after address
handling. Sixteen fixed metadata slots retain only exact aliases. All clobbers,
control transfers, unknown writes and overlapping writes expire the relevant
facts. Existing scalar private transfers and strict checking remain unchanged.

Qualification requires the closed same-capture Load/Copy coverage, four focused
controls and 607 workspace passes/profile (13 ignored), 121 strict Cargo/cache
commands, six exact original profiles and the unchanged changed-source primary.
The workspace count includes three test-only observer controls added after the
600-test private-transfer build and four new runtime controls. See PLAN.md.
