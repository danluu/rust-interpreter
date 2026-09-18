# Runtime workflow controls

All 67 focused controls passed. The ordinary launcher applies explicit compiler
arguments only to application Cargo after clean standard-library lookup; the
benchmark records runtime/shared-std selection and verifies actual arguments,
compiler identities, separate native flags, source histories, and build timing
boundaries. Existing stock routes remain covered.

The first 66-control run exposed an application-flag leak into the VM environment
and an alias in a synthetic expected-flags fixture. Both were fixed; the second
66-control run passed. Independent review then found an encoded-argument check
that conflicted with the native `cargo check` control. Its regression control
and fix passed in the final 67-control run. All three original outputs and input
snapshots are retained; failed evidence is not replaced.

The archive has 589 logical regular-file members. Every member hash and the full
gzip EOF/CRC were checked. Child command/environment/cwd, parentage, timestamps,
raw outputs, and retained inputs were independently reconciled during archival.
The small archive operation ran directly under the canonical workload lock;
it does not claim a separate outer supervisor.

These are synthetic routing and evidence-verification tests, with no native
compiler commands or application latency measurements. They do not establish
application compatibility or progress toward the 0.5-second latency target.
