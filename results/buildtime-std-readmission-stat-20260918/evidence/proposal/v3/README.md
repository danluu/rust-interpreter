# V3 test-only correction for pathlib's cached stat accessor

V3 preserves the complete v2 production file byte-for-byte: scripts/std_mir_readmission.py SHA6a66c05ddb948a6dfdf3082991aaadc1ad8800340e40ce05568df0a4cfc4e58d. The source optimization and its CPython3.14 POSIX guard are unchanged. The parent owns application and execution; neither occurs in this packet.

Source review of the installed Xcode Python3.9 pathlib found that _NormalAccessor captures stat=os.stat at module import and Path.stat calls self._accessor.stat. Patching only os.stat after that import misses actual pathlib calls. The two v2 fault-injection tests would therefore fail their old-runtime oracle without exercising the intended fault. No test run discovered this issue; it was found before C9 execution.

V3 adds a module-level stat_fault(path, failing_stat) context manager using contextlib.ExitStack. It patches os.stat and, when getattr(path,'_accessor',None) has a stat attribute, that accessor.stat. Both patched locations use the same failing callable. No assumption is made that a runtime does or does not expose an accessor. ExitStack restores both patches on ordinary or exceptional exit.

The stable-error test uses the common helper. The transient-error test uses it in separate oracle and validation contexts, each supplied by a new one_shot_fault() closure, so their state is independent. Each context shares its one closure across direct and accessor calls; the same initial fault cannot accidentally fire twice through two independently counted patch targets.

All twelve test names are unchanged. All seven original tests and their setUp/validate helpers are AST-identical. The three other new semantic tests are also AST-identical. The two fault-test method ASTs differ only in the context-manager call; normalizing that call back to patch.object makes them equal to v2. No expected errors, parity fields, artifact checks, success conditions or call-count assertions were changed or weakened.

Files:
- candidate.patch is the complete baseline-f38004 to v3 two-file proposal.
- test-only-from-v2.patch is the exact small test delta for reviewing the already applied v2 tree.
- source-bindings.json records baseline, v3 and previous-v2 hashes.
- production-ast-diff.json and local-version-proof.json are unchanged copies of the v2 production proof.
- test-hook-source-proof.json binds the exact local3.9 pathlib source and cached-accessor/method ASTs, the helper AST, and the test-only normalization checks.

V1 and v2 remain intact. V1's production retry was invalid; v2's production remains sound while its fault-injection harness needed this compatibility correction. The parent will preserve the previously frozen decision and revise only its source/test revision bindings before execution. No numerical gate, case, pair count, process schedule or outcome requirement is changed here.

Qualification remains twelve tests against each actual production arm (24 primary CPython3.14 executions), plus a separately frozen actual CPython3.9 compatibility stage of24 if adopted by the parent. Both stages use the identical candidate test source with canonical production preloading for the selected arm. The older stage verifies the real fallback runtime; it must not be represented by flipping a flag in3.14.

This packet was produced using source reads, hashes and AST parsing only. No project imports, tests, fixtures, compiler/rustup queries, builds or measurements ran.
