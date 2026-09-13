The two runtime Trap location paths passed the targeted scope and diagnostic
controls. These are correctness results, with no timing or speed claim.

- Original attempt01 passed the complete 67-command artifact/scope test, then
  failed an extra application-filename assertion after 15 diagnostic commands.
  Full native/exported diagnostics already agreed; the E0080 application
  callsite was nested inside macro expansion spans. That attempt remains failed.
- The narrow recursive-span assertion correction passed all 63 diagnostic
  commands in attempt02, including unused type/borrow/constant errors under
  four remap scopes and successful restoration after every error.
- Attempt02 reused the earlier scope pass only after proving the compiler,
  prepared std, all three actual tool binaries and every scope-test dependency
  were unchanged. Exact source reconstruction allows only the diagnostic
  helper/assertion correction. No artifact or diagnostic normalization is used.
- Fresh matched Tools06 and Workspace04 passed; the workspace reported 505
  passing Rust tests and four ignored tests. Tools04 and05 timed out during
  lock admission with no Cargo/compiler build child or inner build directory.

The final tool key is
`ee858a5c30c2052959de7e9e132a4e4f39cec9b38fa3fac85777cf69ee6d9f21`,
using compiler
`f9fb3e5f59b8567fffd32c936a9864d0baee77038574236710fbcec75a57d33f`
and prepared metadata std
`4634cc1a80d3698d0c2194cbac1e714596d3492d30e8ca4c030dc3c76ed517c0`.
The three final executable hashes equal Tools03 exactly. The new key records
the corrected test source. Linked native controls use the full compiler sysroot;
metadata/export diagnostic controls use the same prepared metadata sysroot.

`evidence.tar.gz` contains 4,069 verified members (7,528,606 compressed bytes),
SHA-256 `d085d4407102bc29439cad74d1ef98fdfbfdc460a2386301b715f6fa19ee7bcd`.
It retains both raw targeted histories, native/VM stdout and stderr, complete
diagnostic JSON, source snapshots, actual unmodified RBC and MIR dumps,
metadata, exact runner sources, compiler/tool identities, build/workspace
receipts and outer supervisors. Every archive member and retained input was
rehashed after writing. Native/test/tool executables and debug bundles remain
private; excluded executable hashes and sizes are recorded separately.

`summary.json`, `members.json` and `inputs.json` bind the archive and original
files. `archive-supervisor` records the archive process itself. The originals
remain in their owned work directories; nothing was retired by this archive.

The numeric VM file/caller encoding in the scope test is supplemental. Exact
guest file/caller string and coordinate equivalence remains a separate
source-observable prerequisite; these results do not replace it.
