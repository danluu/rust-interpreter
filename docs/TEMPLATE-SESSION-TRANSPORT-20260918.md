# Experimental session transport requirements

The API feature is being qualified before transport is introduced. This design
does not authorize runtime adoption or relax strict Rust checking. The session
owns only its own workers/process; it must never control another session.

Use a separate explicit executable or mode, started by the owning controller.
Begin with a bounded request/response stream over inherited pipes for fixtures
and saved-suite qualification. A private local socket adapter can then connect
independent checked-source commands. Do not serialize templates or native words:
only this executable emits the cached contents, and native arenas are recreated
for each checked Program. No server auto-discovery, stale-endpoint removal or
automatic daemon restart is needed.

Two persistent owning workers each create their own TemplateHistory. Requests
share immutable Program data and an atomic test queue. Each worker creates and
drops a PreparedJit per request; only its bounded history persists. Complete both
workers before accepting another request. A guest failure is an ordinary result;
a worker panic poisons the session and must be reported without hanging joins.

Requests bind protocol version, monotonic request identity, executable identity,
artifact/catalog paths and hashes, requested tests, limits, mode and output path.
Keep parsing, strings, environment input, test count and report size bounded.
Reserve the report before any guest execution. Return an explicit failure for
invalid metadata; do not silently run another route. A lost response must never
cause automatic replay: guest execution may already have occurred. Existing
reports and request identities help distinguish unknown outcomes from no run.

Environment values are per-request inputs. Pass bounded raw byte pairs into the
existing immutable environment snapshot implementation; do not call set_var or
mutate global process state while workers exist. Never log environment contents.
Guest pointers and readonly storage remain per invocation. Bind the caller's
working directory to the session's current directory; reject a mismatch before
execution. Retain existing descriptor/getcwd admission semantics and do not add
new OS emulation or peer-owned application admission changes.

The initial independent-command transport should use an explicitly supplied
private directory/socket and a per-instance secret, matching executable identity
before accepting requests. Bind only a new socket. No existing endpoint may be
removed. Shutdown is a normal request or pipe EOF; the controller waits for its
own process. Server readiness and exit receipts identify exact PID/start/command.

Measure server process CPU around each request, then reconcile total process CPU
at orderly exit. Client waited-child CPU omits persistent-server work. Record
startup and teardown and charge them to the complete edit history; also report
per-command request costs. Compare history on/off in the same session design and
compare complete commands with the adopted fresh-process VM and ordinary native
Rust. Preserve wrong-result edits, restored-source states, ordinary entropy,
dynamic scheduling, two Cargo workers and all prospective primary/noise gates.

The session is worthwhile only if changed-source end-to-end results clear those
gates after these costs. Current in-memory correctness evidence is not a timing
result and does not justify excluding transport or setup.

The socket adapter is qualified at7ce2f250 by endpoint01 (closed). Its25 controls
in each profile include18 owned processes across both profiles, all reaped. Four
expected nonzero exits cover malformed pipe framing and occupied socket directory.
Socket controls cover current callee/data/environment, verified history reuse,
authentication/server identity, schema/sequence/unknown fields, cwd/report errors,
lost response without replay and ownerEOF while waiting in accept. Private token
files remain0600 in0700 directories; published receipts contain only public
identity or file hashes. No independent-command client or performance claim yet.

The explicit VM client is qualified at8bf8d47a by client01 (closed). Nine session
controls/profile launch22 owned servers and32 actual VM client commands across
both profiles. Requests with changed inputs and guest failures preserve current
semantics; wrong modes, stale identity, permissions and reserved outputs fail
without execution. A malformed artifact returns an error and the next valid
request succeeds. The client does not decode the Program or retry requests. A
bounded create-new report sidecar identifies the actual server, CPU counters and
result digest. The next gate connects strict Cargo commands to this client.

Launcher02 is closed at21ee5a94:441 Python controls pass with22 expected skips,
and the feature-disabled VM builds. Launcher01's full run exposed two retired
archive paths in existing tests; it is preserved as failed. Two test-only fixture
bindings select the exact local archives and pass all original hash checks; the
439 earlier successes are reused after exact source-delta verification. Compiler
implementation and peer files are untouched. The explicit client VM is installed
with byte-identical adopted exporter/wrapper under tool9f7aa601253a6817745070cf16a5122282d4fd9f70b33a14b625ee7a09a4a30b.
Actual source-build performance remains unmeasured.
