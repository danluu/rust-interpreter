The publication merge passes 334 Python contracts (16 declared skips),
including all six new owned-compiler tree-inspection boundary tests. Every Rust
and shared compiler input still matches the qualified build, and the immutable
VM/exporter/wrapper binaries retain their hashes. The only changed launcher
helper is custom_compiler.py: an AST comparison proves all code outside its
owned-tree inspection function is unchanged. This preserves the other session's
qualified loader improvement without altering the stock route used by the
completed project histories. No guest command or Rust build is repeated.

The earlier precommit check correctly refused a dirty publication worktree and
ran zero tests. A whitespace check had rejected context lines in the immutable
archived unified diff; the patch was preserved exactly and all other staged
files passed. The successful check runs against the clean committed merge.
