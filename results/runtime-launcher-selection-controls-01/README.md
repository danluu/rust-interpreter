# Native runtime launcher selection controls

All 45 tests passed without skips: eight new runtime association/selection tests,
the existing custom compiler and launcher tests, and source-path std tests.
Cargo and VM children are mocked. This result is not a build-time measurement or
real exporter/application qualification.

The tests cover ordinary runtime routing, exact prepared std selection, early
rejection of missing/conflicting/unsupported selections, no stage2 fallback,
changed runtime identities, mismatched wrapper probes, and distinct tool policies.
Helper 80296 and test child 81010 held the canonical lock from
1789766937.1775548 through 1789766938.9532108. Unittest reported 1.609 seconds.

The archive retains the complete raw command output and receipt, runner, and
181 source/helper/Python inputs. All live and retained inputs were rehashed after
the test. All 185 archive members and the full gzip stream were read back.
Archive creation was a direct root Python operation under the canonical lock;
it does not claim a separate outer supervisor. See `summary.json` for hashes.
