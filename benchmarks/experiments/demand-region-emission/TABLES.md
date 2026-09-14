# Stable demand resume tables

Allocate one zero-filled full-function resume table before region publication.
Retain its pointer for the function's entire lifetime. Acquire a vacant slot
before code commit, then fill it with the checked published continuation without
further fallible work. Never overwrite a published slot or the permanently null
one-past-code continuation. Missing tables/slots retain existing VM fallbacks.

Qualify the two focused metadata controls in debug and release: updates preserve
both inner table and outer pointer-array addresses while other functions allocate,
and the existing aggregate 16 MiB table budget admits its exact boundary while
refusing oversized requests without publishing pointers or consuming charge.
Synthetic aligned slot values are metadata only and are never executed.

These are new APIs; the existing execution path is unchanged. Run complete native,
fault/budget/profile/TLS and original-workload qualification after wiring them into
the demand publisher. All initial plan/block/extra-metadata admission must precede
table publication; after the table is published, region refusal stays on the
demand function's VM fallback path. Do not overwrite it through the eager publisher.
