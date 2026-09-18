# Full parser compatibility passes

One fresh candidate invocation passes all 114 original parser tests, using the
exact retained bytecode and catalog from the qualified compiler. Native outcomes
for the same 114 tests are reused through their retained executable and output.
The candidate enables scalar, resumable, persistent-register and indirect calls.
The original source and assertions remain unchanged; 6,798 frozen inputs match.
This is a correctness check, with no performance claim.

The first supervisor could not obtain the shared lock in 45 seconds and started
no guest. A separate supervisor ran the unchanged controller successfully. Both
terminal histories are retained. Evidence closure has also encountered a lock
wait timeout before performing its audit; the completed tests are not repeated.
The two 88-command changed-source parser histories remain unstarted and required.
