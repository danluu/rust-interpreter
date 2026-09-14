# Conditional policy retains parser coverage

All three fresh profiles pass: adopted entropy record, adopted replay and
conditional candidate replay. The size policy selects demand for the current
parser and reconstructs schema-3 code maps exactly. Every original per-PC count,
peak guest-memory byte and entropy input is preserved.

Of 4,547,956 executed logical operations in the oversized `reduce_cold`, 4,371,681
run natively (96.12%). Total interpreted work falls from 4,831,199 to 1,008,202
(79.13%), reproducing the earlier broad-policy coverage benefit. The unchanged
16 MiB arena holds 16,777,168 bytes. Retained plans use 12,114,321 bytes and
publication metadata 5,591,518 bytes under separate 16 MiB bounds.

The closure verifies 26 frozen inputs and 16 artifacts. This is a fresh-owner
coverage result, not a performance measurement. Proceed to a preregistered
changed-source parser primary; larger histories require that primary to pass.

[Summary](summary.json), [closure](closure.json).
