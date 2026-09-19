# Allocation decoder: finite semantic qualification

Source-only semantic packet. No fixture, project import, semantic controller or
workload was executed while authoring. Parent-executed unit attempt02 passed all
52 exact named tests (7/19 per arm), with eight settled children and identical
389 before/after bindings. Its retained result is now fixed:
unit-screen-02/result.json, SHA
e7db839bee8e417288538ad92b06389001a8442ffe62dce182da67cd5e7e51d0.
Semantic execution still requires parent and independent source review.

The v4 test-only revision preserves the reviewed v3 production source, which removes repeated JSON decoder creation but defers first
construction until the first ordinary record inside its frame-preserving helper.
Source roots are baseline rust-interp-launcher-association-20260918 and candidate
rust-interp-allocation-trace-decoder-20260918, both based on
835382dbe182ebf5f10d322e79ac290cdd3ef2f2. Only allocation_trace.py and the added
test_allocation_trace.py differ. The method/gates are frozen in decision-plan.json,
SHA 4843e329a9f134fb0f4d7a0473509176f23d54bb7f7b2fa6a1bd875a42d12917.
The v4 patch is f9a32243517c0fcf3de19a47f4a686d090f69ca6dec0052f8890a2c3935a6bc4.
Unit attempt01 failed the baseline because a new test incorrectly expected the
installed C scanner to reject depth4096 at Python's recursion limit. Candidate
units and semantic/timing work did not run. That attempt remains preserved.
The corrected nesting test directly requires acceptance of depth32, rejection
of malformed depth32 with JSONDecodeError, and successful recovery with both
scanners; it requires depth4096 RecursionError only for py_make_scanner.
The separate parser-error-details test compares exact exception type/message
and JSON/Unicode fields against public json.loads on first and later records.
All seven tests and frozen qualification/timing counts/gates remain unchanged.
The parser production hash stays
888622f2a5f39c896a440310ce194cfed1bab8d20237338a87f4c5e06a7cb9ff.
Attempt02 passed as recorded above. Drafts before the bounded-copy correction and v4 rebinding
remain in pre-bounded-copy-v4-binding/. No deeper C-scanner samples were added;
the fixed 0..limit+8 ranges prove finite parity, not the C scanner's actual
recursion boundary.

## Fixed seven-process method

One shared benchmark flock covers exactly seven work children, each preceded by
its own memory query: 14 settled children total.

1. Copy only the eight exact real files named in the bound trace provenance into
   one new canonical private real-fixtures tree. Exclusive ordinary-file creation,
   no-follow source open with fstat equal to the recorded source stamp. The copying file descriptor is unbuffered, so copying
   reads at most the recorded bytes plus one, rejects growth before writing that
   extra byte, requires exact EOF/length, and rechecks fd/path stamps. Before/after
   source identity and SHA equality, per-file
   and per-MiB disk guards, destination size/hash equality, then read-only files
   and directories. All source receipts and destination proofs remain retained.
   No original directory or peer target/cache walk occurs.
2. Baseline transport child runs the original 33 rejection cases and exact bound
   success cases, plus four real traces through BOTH actual public APIs.
3. Candidate transport child repeats those same calls at the same paths.
4. Installed C scanner with recursion limit 200.
5. Installed C scanner with recursion limit 1000.
6. stdlib py_make_scanner with recursion limit 200.
7. stdlib py_make_scanner with recursion limit 1000.

Each recursion child pairs both actual implementation sources in the same process
and external call stack, alternating first arm by depth. The default scanner must
be the installed C scanner. Scanner factory and recursion limit are restored in
finally. No implementation hooks, public APIs, validation, file hashing/stamps,
or decoder methods are replaced. Selecting the real stdlib fallback factory is
the explicit protocol variation.

For each scanner/limit, every depth 0 through limit+8 inclusive is tested with
arrays, objects with duplicate-free keys, and alternating array/object nesting:
7308 depth pairs across all four children. A valid three-event trace contains the
nested value in an unknown body field. No timing conclusion uses these inputs.

The same inclusive caller-depth range tests leading first-record BOM and BOM
after JSON whitespace: 4872 additional pairs. Recursive callers catch only after
unwinding. API entry is recorded from actual validate_trace code frames in the
exception traceback (or successful return), not profiling or an inserted API
wrapper. Even failures before API entry must agree exactly.

Each shape also gets nested duplicate fields and all three named nonfinite values
at depths 0,16,64 under every scanner/limit: 144 hook-failure pairs total. Ordinary
1e999 gets the same 36 shape/depth/scanner/limit combinations; it must succeed at
depth zero, while deeper recursion failure may be compared normally. Every pair
is followed by BOTH arms accepting the same shallow three-event trace: 12360
paired recovery checks. The complete finite schedules, order, counts, restoration
and retained JSONL row counts are checked by the controller.

## Exact outcomes and original transport suite

The original script is
benchmarks/experiments/artifact-diff/check_allocation_trace_transport.py,
SHA f1dd0a04fb3476c856c8043a3005a190372a1f6f229061d42017c4abe09f0c7f.
Its malformed-input dictionary and every reject call are AST-identical here.
The original accepted exception classes are unchanged. Adaptations replace only
outer CLI/lock/root/history plumbing and strengthen retention of actual outcomes.
All 33 labels, rejection errors and bound success cases remain required.

Each real trace receives validate_trace and selected_trace; real event counts and
complete selected receipts must match the bound expected records and each other.
Exception type, str, args, explicit cause, JSONDecodeError msg/doc/pos/lineno/colno,
and UnicodeDecodeError encoding/object/start/end/reason are retained. Transport
reports encode byte objects losslessly as complete hexadecimal; strings are
complete. No path normalization is used to manufacture equality.

Filesystem error strings contain absolute paths, so both transport children use
one common task-owned synthetic path. The baseline final inventory is retained.
Before the candidate resets its known regular sidecar or overwrites the known
artifact/case files, every file hash, mode, identity, size and timestamp must equal
that exact terminal inventory. Candidate replay then follows the original suite
mutations (including symlink, FIFO, directory and oversized-sidecar cases).
Baseline/candidate reports and logs are separate and never overwritten. Only the
declared private synthetic files mutate; real fixtures remain immutable and are
reproved before/after every child and at final settlement.

For deep cases, complete Python outcome dictionaries are compared in memory
before compaction. Success/count and full error attributes/cause must agree.
Large document strings are retained by length and SHA only after that exact
comparison; short errors and positions remain readable. Each row records scanner,
limit, shape, depth, caller depth, arm order, input size/SHA, both outcomes,
parity flag and both shallow results. The generator source is bound. Recursion
mismatches are retained throughout the finite schedule and fail qualification;
they cannot be discarded, retried or treated as timing evidence.

## Admission, inputs and receipts

The controller uses the audited C4 child/admission/proof helpers with identical
function bodies. It pins both project Python inventories (186/187 files), source
proposal, original transport script, provenance, three Python executables/
framework identities, JSON/scanner source and the installed _json extension.
Original real inputs are read only by exact named paths. Every child launches
with -I -S -B and explicit -X pycache_prefix to the same new owned empty prefix,
which must stay empty. Drivers load only their specified actual source modules.
Loaded file identities are retained; the fixed implementation and JSON engine
sources are checked before and after the whole qualification.

This is the bounded Python category: >16 GiB direct free disk, >=30% free memory
before every work child, fresh disk before memory queries, read-only five-second
disk observation during children, and exact wait4 settlement in finally even if
receipt writing fails. Rust execution remains gated at 32 GiB. No signals,
cleanup, retries, global caches, network, compiler, Cargo or VM execution.

All stdout/stderr are files; post-exit readers cap each at 16 MiB. Individual
recursion row files are also capped at 16 MiB when read. These bounds are not OS
allocation/output quotas. A crossed resource floor or failed child stops further
work and retains artifacts. Semantic mismatches are reported separately from
procedural completeness; any mismatch prevents timing/adoption. Receipt CPU/wall/
RSS are supervisory accounting only, with no performance interpretation.

After successful unit binding and independent review, root may use the pinned
Python 3.14.7 with -I -B on qualification-controller.py and the explicit
--execute-frozen-semantic-qualification flag. Timing preparation/execution is a
separate future stage and requires successful semantic qualification.
