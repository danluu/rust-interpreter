# Fresh-history space estimate includes the running floor

The original Nushell admission at 18.20 GiB is now rejected. Keeping its historical cache sizes, 20% growth allowance, archive reserve and evidence reserve requires 25.99 GiB after adding the missing 8 GiB running floor. The exact admission boundary and 32 invalid inputs pass their checks.

This helper does not change benchmark controls or historical evidence. It is an estimate; unrelated shared-volume writes can still exhaust headroom.
