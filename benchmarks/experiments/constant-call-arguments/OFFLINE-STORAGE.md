# Fixed-size offline work on the existing filesystem

The measured free space before the next saved-program run is4,307,124,224bytes.
The three original artifacts plus the diagnostic binary total36,998,025bytes.
The existing4GiBfloor would stop after publishing token and before verifying it.
No child has started for the new saved run, and no benchmark gate is evaluated.

Offline fixed-size artifact floor: 3 GiB. Require an additional512MiB at initial
admission. The CLI caps each of three output artifacts at64MiB and each of six
reports at32MiB; together these use at most384MiB, leaving128MiB for the1.2MiB
binary, summaries, plans and receipts. Continue checking3GiB before every child.
Actual previous artifact totals are below37MiB. This explicit allowance applies
only to the offline specialization and retained-VM replay described here.

For replay under this allowance, reuse the qualified replay02 entropy tapes
instead of recording new tapes. Bind them to the prior baseline artifact,
original native assertions, entropy request/byte counts and immutable hashes.
The first baseline run replays that same stream; it is untimed for ratios.
Unexpected requests fail at the replay boundary. The remaining three alternating
pairs use it unchanged. Existing CLI report limits and the12/18/4test selections
bound new reports. No Cargo command, workspace cache, source edit, archive,
deletion, new volume or external service is part of this work.

The host-build4GiB floor and real-project benchmark admission rules remain in
effect. This is a resource allowance for bounded offline files, not a relaxed
performance or correctness criterion. Preserve both failed and passed evidence.
