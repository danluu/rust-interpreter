# Buffer template-key serialization without changing identity

The closed template-phase diagnostic measures median8.883ms/worker in key
serialization/hash, against1.463ms in restoration. Many small bincode writes go
directly into SHA256. Test a fixed4KiB temporary buffer with direct streaming for
large chunks. This targets a measured component, not a claimed command speedup.
Emission on misses remains a larger cost and is not changed by this candidate.

Experimental jit-buffered-template-keys composes the corrected v3 cache and
artifact-digest/size-tier base. Keep the entire serialized key tuple byte-for-byte
identical, including current caller/callee IDs, function count, callee zeroing and
scalar proofs. Check every complete write against the existing4MiB limit before
accepting any byte. Flush only accepted bytes, including the final partial buffer.
No native-code, cache-size, restoration/admission, strict-checking or wire-policy
change; ordinary unbuffered builds remain available. No persistent native cache.

Two stream tests cover zero-length and SHA/block/buffer boundaries, small primitive
and large writes, repeated/interleaved flushes and oversized-write rejection with
no partial acceptance. Run against direct SHA256 in both buffered and unbuffered
builds. Full658Rust tests/profile+16ignored,33diagnostic integrations,10unbuffered
session controls,24unbuffered model tests and default VM build. Reuse only the
unchanged442Python/22skipped record after source/log binding.48servers92clients.

Then replay16saved actual parser suites/1,824invocations with independent fresh
emission verification on every hit. Diagnostic attribution and installation may
follow that gate. Any E2Eprimary uses new namespaces and retains original gates,
complete session accounting, actual source edits/assertions and strict controls.
The previous full guard remains unmeasurable; no unchanged rerun or adoption.

Serialize benchmark.lock45s,two workers,same dedicated buildtarget neverclean.
Buildfloor max(14GiB,8GiB+2*allocated target),replay12GiB/child8GiB. Freeze source
through closures, preserve failures and do not control other sessions or goals.
