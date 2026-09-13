# Completed public Nushell cache retirement

Nine exact custom namespaces from three completed132-command public Nushell
comparisons were retired under the shared benchmark lock and each namespace's
invocation lock. Sources, bytecode, catalogs, raw evidence, installed tools,
executables and libraries are retained. All47,083 protected-file hashes pass;
the pre-interruption protected manifest also passes.

The final pass removes101,608 nonexecutable compiler intermediates totaling
37,224,037,836 logical bytes. Reported free space increases from13,550,706,688
to37,389,504,512 bytes (about22.2GiB); this is observed filesystem movement on
a shared APFS volume, not a one-to-one logical-byte claim. Nushell's frozen
50,500,745,555-byte admission still requires more headroom.

Two initial checks rejected the cleaner's own held lock before any deletion.
The next attempt removed164 files, then stopped because unlinking a hard link
changed a sibling's link count. Its audit found only23 link-count differences;
no remaining file's inode, size, modification time, mode or block count changed.
The final pass revalidates device/inode/size/mtime/mode before every unlink,
allowing link counts to decrease as earlier links are removed. All failures and
the partial929,301,114 logical bytes remain recorded. No process was signaled.

[Summary and immutable receipts](summary.json), [final driver](driver.py).
