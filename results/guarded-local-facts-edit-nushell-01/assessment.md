The original Nushell type-relations comparison passes all132 commands and its frozen regression guard. All14 original tests have matching native/custom outcomes, deliberate wrong edits fail, restored source passes, and paired custom bytecode/catalog hashes agree. The full final audit verifies the recorded inputs and source restoration.

Candidate/prior-custom paired wall is1.0011465106 and CPU0.9971053055. A/A envelopes are0.0404495945 and0.0083683410; wall/CPU margins are1.0415961051 and1.0054736466, both within1.05. This is effectively unchanged against the prior custom runtime. Candidate/ordinary-native wall is0.6118931275 for these selected edits and14 tests, with matched two-worker Cargo settings. No whole-shell or cold-build speedup is inferred.

The unchanged47.0325 GiB admission succeeded only after verified cache retirement. All original132 commands ran once. The preceding594 commands from the other cases were retained and were not rerun.
