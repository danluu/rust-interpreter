# Explicit startup environment adapter

This is an unexecuted source proposal. It leaves the qualified runtime04
directory, original01 Controller, and all four qualified audit05 reader/IO/test
files unchanged. Its 39 controls are written but unrun: 20 pure environment
cases, four early admission checks through the unchanged Controller, and 15
complete saved owner fixtures for both runtime phases and negative mutations.

The read-only rehearsal02 preparation actually passed an environment without
`__CF_USER_TEXT_ENCODING`; its child observed `0x1F5:0x0:0x52` before factory
imports and at completion. Those are actual preparation observations. The later
Reader02 failed because its physical table omitted three completed hash-owner
inputs. Neither event is a runtime Controller execution.

`environment.py` preserves each raw string and distinguishes the actual passed
preparer environment, observed preparer environment, workload environment, and
explicitly planned launcher environment. Every passed key/value must survive
unchanged and all preparation samples must agree. Only Darwin may add the
bounded CF triple already admitted by the qualified hash stage; its first field
must equal the actual integer UID. Unknown additions, changed/missing values,
wrong UIDs, malformed triples and conflicting existing CF values fail closed.

The launcher mapping is a detached copy of the unchanged workload mapping plus
the exact observed CF value, when present. The helper never reads or changes
`os.environ`. Non-Darwin observations must match the passed mapping exactly;
the concrete runtime preparer remains bound to the existing Darwin UID501 owner.

`prepare.py` is a narrow standalone derivation of runtime04's preparer. Its
explicit `HERE` stays the original runtime04 directory. The enclosing reviewed
preparation wrapper authenticates the full source closure, places this adapter
then the qualified runtime04 directory on its import path, and executes the new
artifact. The factory, Reader, entry, recipe, Controller and private monitor are
the existing qualified sources. The two original packet names remain fresh:
`preflight-plan-01` and `installation-plan-01` under runtime04. No packet or WORK
has been created by this proposal.

The producer requires actual separately audited startup controls before loading
the pure policy. Its CLI additionally requires `--startup-audit-sha256`,
`--preparation-passed-environment-json`, `--preparation-record`,
`--startup-source-manifest`, and `--startup-source-manifest-sha256`. The source
manifest is `{status: "reviewed-runtime04-startup-source-closure", files: {...}}`,
where every file row has exactly `sha256`, `size`, and the seven stable identity
fields. The manifest excludes itself; the invocation authenticates its raw SHA.
The producer retains the manifest and all rows as selected snapshot inputs and
rejects differing overlaps. Source bindings also retain the three exact
completed hash-owner rows from the independently derived Reader dependency
census and require all 1,256 named Reader dependencies in the physical table.

The packet keeps `plan.environment` and all recipe children unchanged. Only
`plan.launch_environment`, the freeze launch environment, and launch proposal
environment receive the explicit launcher mapping. `plan.startup_environment`
has exactly:

- `derivation`: policy, platform, UID, actual passed mapping, raw observations,
  and explicitly planned launch mapping;
- `policy` and `preparer`: exact source path/SHA references;
- `qualification`: actual source/control qualification returned by the existing
  complete bounded-control reader;
- `preparation_record`: the canonical phase-specific execution04 record path;
- `source_manifest`: the authenticated supplemental closure reference.

The three raw observation names are `before_factory_definitions`,
`after_factory_definitions`, and `before_packet`. Metadata preflight adds the
actual completion environment. No future controller observation or future
record digest is fabricated. The original Controller still requires exact
equality with the explicitly passed launcher mapping; a later unexpected
startup change still fails before runtime WORK creation. Compiler and probe
commands continue to use the original workload mapping and exact recipe checks.

`audit_owner.py` replaces only the owner call in a separately reviewed audit
orchestrator. It receives the original qualified reader as `original`, an
independently authenticated `workload_environment`, and a
`validate_qualification` callback that must return exactly `True` after reading
the actual new controls. The caller derives the workload mapping from the
authenticated hash plan plus the exact owned TMPDIR. It must not derive that
expectation from the candidate plan being checked.

The owner keeps every original phase, PID, timing, packet, source, raw output,
handoff, scope and capacity predicate. Its environment relation verifies the
raw plan and explicit startup derivation directly; it never feeds a rewritten
plan to the old owner. The existing reader's child history, snapshot accounting,
catalog and phase predicates remain independently required.

Besides original owner arguments, `expected` supplies `preparation` and
`preparation_launcher`, both exact path/SHA references supplied only after actual
preparation closure. The declared record must be finished/rc0 with
`preparation_passed: true`, correct source/invocation/command, and plan/inputs/
launch output hashes. The wrapper must retain `child_observation_sha256` in its
final record. The owner compares that raw observation's passed and observed
environments and checks its actual child identity and chronology, including completion before
the original runtime owner starts. The plan
contains the future record path only, avoiding a self-referential plan digest.

Root owns `runtime04-prepare-launch-01/prepare_once.py`, which consumes
`invocation.adapter = {preparer, source_manifest, startup_controls}`. The last
field references the actual startup independent audit. The wrapper keeps the
original packet owner, adds current supplemental source rows to the separately
qualified rehearsal closure, and invokes this artifact. All actual new
qualification pins remain unset in `source-bindings.json` until a separately
approved bounded run closes.

The pure controls import exactly seven local source files: the four new
policy/owner/test files, original01 `controller.py`, and immutable audit05
`reader.py` plus `test_reader.py`. The original test file supplies in-memory
fixtures; its tests are not implicitly rerun. Tests use fake paths and a fake
Controller `os` namespace, never modify the real environment, and stop before
specification/provider/WORK activity. Preparer source is separately reviewed,
not represented as executed or qualified by these metadata fixtures.

All admission thresholds, canonical lock ownership, resource ceilings, snapshot
limits, evidence reservation, retirement gates, provider roles, two source
probes and final installation recipe remain unchanged. No runtime preparation,
compiler call, provider probe, retirement, benchmark or test was run here.
