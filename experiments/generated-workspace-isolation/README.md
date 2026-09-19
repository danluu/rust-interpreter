# Keep generated workspaces independent

The first options-hash compiler build stopped before Rust compilation because
the bootstrap package, excluded by Rust's inner workspace, discovered this
repository's outer workspace. Its parent only excluded two named projects.
The fix excludes the entire generated `.work` subtree while preserving
the four ordinary workspace members. It changes no compiler or application file.

Cargo's [workspace documentation](https://doc.rust-lang.org/cargo/reference/workspaces.html#the-members-and-exclude-fields)
describes parent discovery and exclusions. Its
[workspace source](https://doc.rust-lang.org/stable/nightly-rustc/src/cargo/core/workspace.rs.html#1985)
matches excluded directory prefixes, with explicit membership taking precedence.
Six offline controls passed with the acquired Cargo 0.100.0-beta.3
(`5f94df478`, 2026-08-27). They verified the actual prefix behavior before the
build continuation; they did not compile Rust or measure application speed.

`controls.py` supplies six offline metadata calls for an admitted controller.
It creates a fresh sibling fixture with an outer workspace and a nested Rust-like
workspace whose bootstrap package is excluded. The original outer manifest must
reject bootstrap; the proposed exclusion must let bootstrap resolve independently.
The ordinary outer member and inner compiler/helper membership must stay exact,
and an unlisted package outside `.work` must still be rejected. Every source and
raw result remains available. The six exit codes were 0, 101, 0, 0, 0, 101, as
expected. The fixture target directory was never created.

The actual history is retained in
`rust-interp-runtime-exporter-20260918/.work/hir-options-hash-workspace-controls-01`,
with its controller under `experiments/hir-options-hash/workspace-controls-01`.
The terminal receipt SHA-256 is
`3deb54a64ea2108b21f10483fa7dfc32914f6145ea0afc913dfa6004423d9c58`;
the controls result SHA-256 is
`5f7fd3cde25c3d650503df71ad444cc13022ea7dd6c3c5cc2a960685f41f101d`.

The control module does not launch itself. The caller must bind the actual Cargo
and rustc providers, hold the canonical lock, retain complete command receipts,
and guard the fixed source/provider inputs. The original failed build and its
already extracted stage0 files are retained for a separately frozen continuation.
