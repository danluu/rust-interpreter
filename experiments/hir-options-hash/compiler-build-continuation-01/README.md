# Continue the compiler build after exact test-name correction

The original build02 completed sixteen commands successfully, including the
lowering check, twelve extracted-provider loader probes and all 27 lowering
tests. Its controller then rejected three fully qualified test names because
the old source-derived expectation used `effects::tests`; the pinned source
actually declares `#[cfg(test)] mod replay_tests`. The failed receipt, raw test
order, expectation catalog and all child histories remain unchanged.

This separate continuation corrects only those three expected prefixes and
binds the complete source module/cfg routes. It rechecks all sixteen saved
command records and replays saved loader outputs without invoking those tools.
It checks exact current build and expanded-registry outputs after admission,
then runs only the original final nine commands: native compiler/std build,
version and real loader probe, sysroot/help, 18 interface tests, run-make-support
build, and two Git postguards. No successful check, loader probe or lowering
test is rerun. Compiler, bootstrap, application and candidate patch bytes do
not change.

The original namespace, canonical 600-second lock, 24 GiB entry, 9 GiB live stop,
8 GiB floor and 14 GiB aggregate namespace cap remain. The copied monitor changes
its fresh evidence directory and counts both previous compiler-build histories
in the same 256 MiB aggregate evidence cap; original evidence is immutable and
fully bound as input. Internal bootstrap
hardlink bookkeeping retains the existing narrowly scoped ctime/nlink
observation rules; provider bytes and stable file/route identities stay exact.

The new terminal's `commands` contains only nine actual continuation commands.
The final `compiled.json`, if successful, additionally contains an ordered
`command_history` of the saved sixteen plus new nine exact receipt references.
This explicit two-history binding is required by downstream native recipe and
B3 preparers. A completed build still does not qualify the native run-make
recipe, B3 composition, session hash driver, installed runtime, applications,
or any performance improvement.

Thirteen fast saved Git/otool children have unavailable contemporaneous cwd
probes. Their recorded requested cwd and observed ps PID/parent/command remain
bound; the continuation does not claim those missing cwd observations existed.

Status: source-only preparation, no continuation launched.

The new monitor's synthetic controls cover the combined evidence limit, exact
threshold behavior, unavailable allocation samples, and signal refusal when
original/current root or member ps/cwd probes are unsuccessful or empty. The
original five failed-supervision drain controls run against the same new
monitor. Every process API in these tests is mocked.

Control attempt 01 stopped before admission or a test child at its helper
`os.environ` equality assertion. Its frozen source and outer failure remain
unchanged. The distinct attempt 02 uses the compiler controller's existing
rule for macOS's optional, UID-validated `__CF_USER_TEXT_ENCODING` variable,
records the actual helper environment, and preserves the first failure. No
completed control test is repeated.
