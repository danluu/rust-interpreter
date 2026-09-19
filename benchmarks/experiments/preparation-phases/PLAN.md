# Attribute preparation before another optimization

The shared-template primary failed; its closed receipt audit shows roughly200ms
of overlapping compiler intervals still present and only5.6ms of added store
construction. Do not retime the unchanged candidate or optimize only that small
constructor. Restore adopted Rust/Cargo sources before adding this diagnostic.

Stage1 introduces a bounded trace recorder behind cfg(test) or the explicit
preparation-observer feature. No JIT, constructor, guest or CLI path uses it yet.
Six controls cover function/phase identity, nested-scope separation, capacity,
counter overflow, error/unwind completion, snapshot ownership, worker isolation
and serialization. Run both profiles with the feature enabled. There is no
executable-code publication or original guest execution in this stage.

The recorder keeps at most65,536(function,phase) buckets per owner. Saturation
and arithmetic overflow mark snapshots incomplete. This is a bucket bound, not
an allocator-RSS promise. Rc confinement matches the existing JIT owner; only
owned plain snapshots may cross threads. Keep all interval categories separate:
parent intervals include child phases and worker intervals overlap. Never sum
these as CPU time or recoverable end-to-end savings.

After recorder qualification, instrument constructors, scalar proof/lowering/
emission/publication, ordinary emission/publication and enclosing preparations
under the same explicit feature. Use a standalone diagnostic executable, since
the existing original-workload observer requires a main thread rather than a
libtest entry point. Preserve strict checking, limits, budgets, native outputs
and error behavior. Reuse original artifact/catalog/native-outcome evidence;
do not edit workload code or assert that the two declined owners are expensive
until their function IDs and intervals establish it. Observer overhead is not a
speed measurement. Ordinary builds must contain no diagnostic fields or calls.

Serialize all checks with the root benchmark lock,45-second admission and two
Cargo/test workers. Use only the existing root target; never clean it. Initial
build floor max(14GiB,8GiB+2*allocated target),8GiB before every child. Freeze
sources before running and close every attempt before correction. Preserve all
successful commands if later observation or bookkeeping fails.

Stage2 instruments only feature-enabled builds and adds a dedicated binary.
Eight focused controls/profile include the six recorder controls plus real
native scalar/ordinary staging, capacity decline, preparation once per owner,
constructor scope identity, and exact success/error/recovery outcomes. Retain
the release observer from Cargo's explicit executable message and check an
ordinary no-feature lib/VM build separately. No original workload is run here.
The observer accepts only prepared suites with at most two workers. Report
serialization failure is separate from original test outcomes; incomplete traces
cannot support optimization inference. Per-function prepared/no-entry facts do
not claim exact decline identity; aggregate compiled/declined counts remain
available. Ordinary publication includes final admission and decline handling.
Successful commands and a copied observer survive any later-stage failure.
