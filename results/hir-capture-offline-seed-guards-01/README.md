# HIR copied bootstrap seed guards

All six Python tests passed with no skips against source commit `af9c37f427fb1447c1219c0e828dc71ceedbd8dd`. The two existing configuration guards remain, plus four tests covering exact cache destinations/distribution environment, missing or corrupt copies with restoration, file/ancestor symlinks, and non-file archive paths. All ten frozen inputs remained unchanged.

The archive retains raw output, command/environment, Python identity, exact source and unchanged bootstrap inputs, process receipts and completed test supervisors. All members were read back byte-for-byte. Archive supervisor completion is retained separately. Originals and the historical two-test result (`../hir-capture-configuration-guards-01`) remain intact.

The source checks copied archive hashes before each `./x`; these tests do not invoke bootstrap or any downloader. Source inspection establishes that `RUSTUP_DIST_SERVER=file:///dev/null` constrains distribution fallback only. CI LLVM uses a separate server; this is not a complete network sandbox or a guarantee against mutation after preflight.

No plan, compiler checkout, compiler check/build, benchmark, or HIR cache-hit qualification was performed.
