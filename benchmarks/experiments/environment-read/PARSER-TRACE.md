# Diagnose parser constant sharing without changing the engine

The stopped incremental benchmark completes 22 commands with matching original
assertion outcomes, but its repeated original artifact differs. Typed decoding
finds 32 more readonly bytes, 2,650 changed functions whose headers are identical,
9,121 changed immediate operations and no changed opcode kinds. A further
`syntax error` occurrence appears in the serialized artifact. This resembles the
earlier traced Nushell allocation-sharing behavior; it is not yet a causal
explanation for pgrust and does not justify coalescing pointer-bearing constants.

Run eight explicitly diagnostic custom commands: original, wrong initial
lookahead, cumulative edit5, original in two fresh independent Cargo histories.
Use compiler incremental mode in both, automatic function reuse off in both,
and the existing bounded allocation observer on in only one. This separates
compiler MIR history from function-template reuse. Each command runs all114
original tests with the existing strict flags and two prepared/Cargo workers.
Compare every outcome with the verified native first-cycle records. No native
command or stopped benchmark command is repeated for a timing result.

Require byte-identical observer-off/on artifacts and catalogs at each matching
history state, every trace's completed artifact binding, exact source edits,
source restoration and all frozen inputs. Preserve original/restored differences
as observations. Do not normalize immediate values or allocation identities.
Trace any extra exact `syntax error` allocation through the existing origin
events and compiler allocation IDs. An absent reproduction stays a negative
result. No speed conclusion comes from these instrumented commands.

Initial admission14GiB,8GiB per child, shared45-second lock, no other own build
or benchmark in parallel. Trace bounds remain the qualified one-million-event,
64MiB output limits. Stop on a bound, guest/support error or observer difference.
