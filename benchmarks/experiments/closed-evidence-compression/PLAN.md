# Test transparent compression before touching retained evidence

Storage admission prevents the remaining parser and Nushell histories. Before
considering any closed evidence, test the built-in macOS ditto filesystem
compression on two disposable, newly generated, non-executable fixtures: repetitive
JSON and deterministic incompressible bytes. This is a filesystem compatibility
check, not a runtime or real-data compression benchmark.

Under benchmark.lock/45s,12GiB initial and8GiB per child, copy one fixture at a
time with explicit --hfsCompression and --noclone. Preserve normal reader bytes,
size, mode, timestamp and a synthetic extended attribute; check seek and mmap
reads. Copy back with filesystem compression disabled and verify the original
bytes and metadata again. Record actual allocated blocks and compression flags,
the system tool hash, commands and identities. Reject the strategy if the
repetitive fixture does not compress or ordinary readers observe any change.
Keep the original fixtures intact. No source, executable, installed tool, shared
target, existing evidence, private data or peer file is modified. Independently
close the compatibility result before designing any real-data operation.

Any later proposal must select exact completed owned non-executable evidence,
prove closed ownership and immutability, preserve every path and plaintext hash,
verify all relevant metadata, exclude symlinks/hardlinks/shared/live files, and
check open files and inode identity under the shared lock. No broad compression
or cleanup is authorized by this fixture check alone.
