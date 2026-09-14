# Private scalar Call ABI qualification

This revision retains live VM pointers x0–x2 across guarded scalar Calls. Private
arguments and Output use caller-SP offsets, x21 is the original logical base,
and status returns in x9. Callee spills have checked encoding bounds. Both
success and private failure preserve the caller convention and exact accounting.

Full qualification requires 597 workspace passes in each profile (12 ignored),
21 focused body/bridge controls, strict Cargo and environment negatives, and
exact original-test profiles before the prospective changed-source benchmark.
See PLAN.md for ownership, resource, semantics and benchmark gates.
