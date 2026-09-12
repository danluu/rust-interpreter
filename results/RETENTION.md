# Evidence retention for new experiments

Commit the implementation and a compact result: assessment, summary and gate
decision. Keep exact commands, logs, source snapshots, artifact hashes and any
failure seed accessible through those summaries. Private results expose only
aggregate measurements and hashes.

Detailed per-file cache inventories and transient collection shards belong
under `.work`, not in new thousand-line Git receipts. Completed disposable Cargo
caches may be removed only after checking exact task ownership, terminal child
processes and open files, and keeping required source/artifact/evidence copies.
An absent results-index entry or an old timestamp alone is insufficient.
Do not archive a disposable cache simply because it can be archived. Installed
tools, executed bytecode, source snapshots, private caches and unrelated work
are excluded from automatic cleanup.

Existing committed reports, inventories and their linked paths remain intact.
They describe historical qualifications; this policy does not retroactively
delete evidence or rewrite failed decisions. New revisions use Git commits in
one experiment directory. Use Git tags/commits instead of new duplicated state
documents. Storage maintenance is outside performance timers.
