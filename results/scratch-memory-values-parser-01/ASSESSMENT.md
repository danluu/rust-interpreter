# All 114 original parser tests passed

The exact qualified df4006e0 / VM 6ac4dd9e candidate passes all 114 original
parser tests with scalar Calls enabled, two prepared workers, ordinary OS
entropy, the existing runtime limits and a 16 MiB JIT arena. The original
native assertion inventory and exact compiler-produced bytecode/catalog are
revalidated from their completed qualification. All 6,719 frozen inputs and
source restoration checks pass.

This is compatibility evidence from one complete suite command, not a parser
performance measurement. The matched edited-parser comparison and the remaining
Nushell full guard are still required before adopting the runtime composition.
