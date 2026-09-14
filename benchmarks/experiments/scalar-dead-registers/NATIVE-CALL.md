# Scalar dead-register qualification

This revision adds bounded dead-register elimination to the guarded scalar
Call composition. It retains every memory access, stack adjustment, branch,
failure tail and return, and relocates branches before native publication.
Unknown encodings or unsupported control flow preserve the original body.

Full qualification requires 596 workspace passes in each profile (12 ignored),
20 focused body/bridge controls, strict Cargo and environment negatives,
and exact original-test profiles before the prospective primary benchmark.
See PLAN.md for ownership, resource, semantics and benchmark gates.
