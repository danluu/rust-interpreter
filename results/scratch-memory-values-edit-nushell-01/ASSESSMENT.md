The132-command Nushell guard passes all original, wrong-edit, five-valid-edit and restored-source controls across three cycles. All14 original type-relation tests retain their expected outcomes. Candidate/control bytecode matches within each source state, and source restores cleanly.

Candidate/baseline median wall ratio0.999955 and CPU ratio1.000212 are effectively unchanged. The2.485% wall and0.856% CPU A/A envelopes produce margins1.024804 and1.008776, both within the unchanged1.05 guard. Candidate/native wall ratio is0.636326. These results cover the selected type-relation tests, not the whole shell.

The comparison retained the existing source/tool pins, six independent caches, two Cargo workers, full strict checking, normal entropy and16 MiB arena. The initial47.03 GiB admission and8 GiB per-command floor were preserved. See the complete campaign closure for the final source/artifact audit; runtime integration remains pending.
