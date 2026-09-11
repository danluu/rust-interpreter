# Preserve Cargo's macOS cache markers

The fourth archive qualification passes all 40 rejection checks and four
coordinator scenarios. It restores the two root attributes observed in the
first real Nushell preparation: `com.apple.fileprovider.ignore#P` and
`com.apple.metadata:com_apple_backup_excludeItem`. Their exact byte values,
file contents, internal hardlinks, permissions and access/modification times
survive the round trip. Archives without the optional attribute field also
restore successfully using the preserved qualification03 fixture.

Unknown root attributes, malformed values and either allowed attribute below
the root are refused. The macOS Python installation lacks `os.listxattr`, so
inspection and restoration use the system `xattr` command. Values are bounded
to 4 KiB each and stored as hex in the validated manifest. This is support for
two observed Cargo markers, not general metadata or ACL preservation.

The coordinator checks retain their previous coverage: successful retirement,
partial archive write failure, archive verification failure and an injected
journal failure after 1,000 fixture paths have been retired. Failed attempts
remain reserved against blind retries, and the verified archive restores all
1,006 original paths after the partial retirement. Outside evidence stays
unchanged. No real compiler cache is modified by this qualification.

The [summary](summary.json) records the exact source hashes and attribute
values. Supervisor 28172 and worker 28175 finished with status 0. The first real
preparation's refusal remains in
[its report](../interface-nushell-native-cache-archive-01-prepare/summary.json).
