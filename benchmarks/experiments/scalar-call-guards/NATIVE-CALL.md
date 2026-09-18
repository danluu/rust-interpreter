# Guarded native Call qualification

This revision carries the qualified scalar local-register emitter and adds
guarded caller-frame arguments and a private entry whose budget is checked by
the Call boundary. Standalone scalar entry budget checks remain enabled.

Full qualification requires 594 workspace passes in each profile (11 ignored),
18 focused body/bridge controls, the strict Cargo and environment negatives,
and exact original-test profiles before the prospective primary benchmark.
See PLAN.md for ownership, resource, semantics, and benchmark gates.
