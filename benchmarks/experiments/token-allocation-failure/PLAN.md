# Fresh token allocation failure

A nonincremental fre export passes native controls but fails the first of three
custom token tests with a guest capacity/allocation trap in RawVec::grow_one.
The new artifact also fails ordinary execution on the older JIT, new JIT and
interpreter, and fails prepared isolation. The older exporter reproduces the
failure under the same explicit nonincremental Cargo profile and MIR flags.
This is evidence of a latent lowering problem, not a PreparedJit-only fault.

Preserve exact passing and failing artifacts. Compare the RawVec path, then
reduce the responsible operation or compiler configuration into a native/custom
fixture. Do not avoid the failing path, change expected assertions, synthesize
allocation success, or classify a trap as an expected wrong-edit failure.
Keep strict checking, the original runtime limits, two workers and 8 GiB floor.
After a fix, qualify both incremental histories and fresh nonincremental exports,
then rerun the complete affected source-edit command. Hold catalog publication
until this fresh-export correctness gap is understood and repaired.

Automatic suite discovery follows this correctness work. Prepared/fresh timing
results already published remain descriptive, restricted to their recorded
artifacts, profiles and edited histories.
