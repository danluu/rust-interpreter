# Restored source reused the final edit's executable

An isolated native Cargo fixture reproduced the problem. Original `answer() = 1`
passed; changing it to 2 rebuilt and failed the original assertion. Restoring
the staged original source bytes then returned the same failure without
recompilation. The staged backup had been created before the edited build, and
renaming it back preserved that old modification time.

All three commands and their outputs are retained locally. This affects commands
after restoration, including warm anchors, rather than measured edit rows that
explicitly require recompilation. See the [fixed regression](../source-restore-after-01/assessment.md).
