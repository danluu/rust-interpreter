# Verify archive prefixes after a space or lock rejection

The assessor now recognizes the exact pre-application space rejection as well
as the existing lock rejection. It verifies every remaining original inventory,
source/evidence map and closed-file state before describing that suffix as
untouched. Failures after archive writing begins remain excluded.

Fifteen invalid classifications reject, including an in-application disk-full
error, mismatched child order, missing/duplicate launch records and a failure
before the next child starts. Both supported rejection types pass. The actual
seven-target prefix and remaining original target verify, and the preceding
24-target completed batch reproduces its prior fields except the assessor
hash. Two added fields explicitly record rejection and remaining-inventory checks.
Supervisor 28102/controller 28105 finished successfully. No cache was mutated.

See [qualification](summary.json) and
[actual partial batch](../worker-cold-storage-batch-03/partial-summary.json).
