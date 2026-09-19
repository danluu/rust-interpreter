This is a fresh attempt to run the two metadata probes required before installing
the options-hash compiler candidate. Attempt04 ended with no compiler children:
available space fell from 26,501,152,768 bytes at launch to 23,099,760,640 bytes at
the controller's 24 GiB admission check. Its packet and failed records remain
intact in `results/runtime04-preflight-capacity-failure-01`.

The new attempt uses separate packet, preparation, controller, launcher,
supervisor and audit paths. It acquires the shared workload lock before the
expensive input checks and retains that same descriptor through the controller.
The launcher evidence directory is declared in advance so that its creation
cannot invalidate the evidence accounting.

Preflight now requires 16 GiB free at entry, while retaining the 9 GiB stop
threshold, 8 GiB floor and 256 MiB evidence cap. This is a phase-specific resource
policy: the recipe contains exactly two sequential, expected-E0080 metadata
compilations of a 57-byte source file, without a linker or installation. The
previous snapshot projection required about 2 MB of new compressed storage and
44.5 MB including reservations. These figures support a smaller admission
reserve; they do not establish a maximum RSS or swap requirement. Preparation
recalculates evidence and snapshot reservations. Installation retains its 24 GiB
gate.

The original qualified runtime modules and environment policy stay at their
original paths. Separate focused tests must qualify the changed routing,
ownership and admission checks before this attempt runs. Old test counts do not
qualify changed source. The correctness checks, full input verification and
compiler probe recipe are preserved.

This directory is not an application benchmark or evidence of a speedup.
