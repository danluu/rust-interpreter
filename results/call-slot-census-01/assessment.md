# Census admission failure

The first census stopped before building or reading any profile. Its driver
expected the smoke execution receipt to hash `commands.json` directly; that
receipt instead hashes the summary containing the complete command list.

The corrected check verifies that recorded summary hash and requires its full
command list to equal `commands.json`. This preserves the same exact invocation
binding. No runtime, benchmark input, profile or measurement criterion changed.
The failed driver source and terminal status are preserved here.
