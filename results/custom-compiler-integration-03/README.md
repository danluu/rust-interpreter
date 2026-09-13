# Preliminary custom compiler integration

Integration03 passed all 36 commands using the same installed custom stage2 compiler and toolset for stable-CGU off/on. The controls covered ordinary pinned Rust native output, custom native host build scripts/proc macros and guest execution, actual body edits, compiled restoration, and 24 expected uncalled type/borrow/constant/panic-error rejections. All 33 workload commands were validated; the other three prepared the two standard-library namespaces and local lockfile. Off/on bytecode matched, edits changed it, and restoration recovered the original bytes.

This is a **preliminary mechanism result**. Diagnostic presentation remains incomplete: 18 missing standard-library snippet occurrences are preserved as explicit gaps. The harness verified source bytes at the public, installed and both prepared std locations, checked every affected byte/character coordinate, and used a separate source-derived comparison view. Raw compiler records and paths are retained. Full presentation qualification, final-target eligibility and adoption eligibility are all false. No performance claim is made.

The final harness revision is `4ec11d3df02d3a9f817fcf950112dac764920b9c`. The toolset's source producer remains `ef8a13c7e255260d3c883943db2b0021f67e981f`; subsequent changes affected only the harness/evidence. The compiler's separate source/package identity is recorded in its installed manifest. The matching workspace correctness run passed 481 tests with one existing ignored test. The archive also retains the prior tool build and its prior-source test result, separately identified in their receipts.

- Compiler: `60096d7efe02d38269c5694bfd046d4f9facfb65139b2d82173d12345a1c9c46`
- Tools: `3b34bb25f0887db0e7a9151b439a28fd6410c441da4d760e2d612f0c46058ebe`
- Std off: `7ecc9c55babac970b04c04d5ce36119a8eec50b0245da844b5517ee800020329`
- Std on: `c982acb3459ba9fdf7699d68016791d52fa422eec42af44364a597c9de257085`

The two failed strict integration attempts and corrected mocked-test admission evidence are retained in the [diagnostic failure archive](../custom-compiler-source-diagnostics-01/README.md). No failed attempt was rewritten. Integration03 used a fresh fixture/cache and the canonical campaign lock; its outer supervisor held no lock. Supervisor54832 and helper57623 exited successfully and released the lock.

`evidence.tar.xz` contains the exact plans, process receipts, command outputs, source snapshots, compiled fixture bytecode, source-comparison proofs and installed identities. The immutable compiler/tool binaries and prepared std metadata remain at their recorded paths. `members.json` records each member's original path, length and SHA256; all 142 archived members were reopened and compared with their captured bytes.
