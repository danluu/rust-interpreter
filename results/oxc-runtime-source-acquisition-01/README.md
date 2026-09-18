# Oxc source admission for the published runtime

The fixed Oxc plugin-normalization case now has an independently copied source checkout under the runtime owner and all 323 required registry packages available offline. No compiler or application test ran in this acquisition, and this result makes no interpreter/JIT compatibility or performance claim.

Oxc remains pinned to `4d5c812d6b16c23fa71d106cf87f7f20ddee69b1`. The source has 16,907 inventoried entries. The copy preserves every source and Git byte except the explicitly changed ownership marker, preserves the two contained source symlinks, and shares no regular-file inode with the qualified original checkout. Profiles, features and tests are unchanged.

The successful launch `06` produced `.work/oxc-runtime-source-acquisition-02/receipt.json`. It passed all 17 focused copy/lock controls and all nine planned child commands. Under Cargo's ordinary download lock it added 95 previously absent archive/tree pairs and 52 absent sparse-index files. The 228 existing package pairs and existing index bytes were preserved. Both the qualified private registry and all 323 final shared packages were checked against their locked archive hashes and exact extracted membership/bytes. The Cargo lock was released before the next child command.

Launch `04` is retained as a preflight failure: the generic input validator rejected the already-recorded 78 hardlinks of Apple's `/usr/bin/git`. It ran no child and made no source/cache write. The correction allows a recorded system executor's existing hardlinks only when the direct resolved path, complete stamp and bytes are bound. Source, cache and copy outputs retain their single-link requirement. Unexecuted proposals `01`, `02`, `03` and `05` are retained separately; none is counted as a run.

The canonical benchmark lock had a 600-second admission bound. Capacity remained 16 GiB at entry, 9 GiB to stop and 8 GiB at the supervisor floor. Recorded allocation was 230,363,136 bytes, including 26,693,632 bytes of evidence; free space after acquisition was 31,021,264,896 bytes. No existing process, cache object or source checkout was removed or replaced.

`evidence.tar.gz` contains all nine raw child receipts and outputs, outer launcher/supervisor receipts, all 142 frozen successful inputs, the exact failed preflight inputs, preserved unrun snapshots, all four acquisition plans, copy intents, complete source/registry inventories, and the independent verification script/result. Large source and registry payloads remain at their recorded owners; their complete byte inventories are archived. Extraction recreates paths relative to the experiment worktree; absolute paths inside records describe the original execution environment.

- Terminal receipt SHA-256: `307d80821038a5552432ebaf6549b4910c63670b746e1a8dbe0574571b8e24cb`.
- Independent verification SHA-256: `7b3d884ba85da7c66dd5a3db3276e5ffac0b46fe77e422a7ea1f43ca24b4420a`.
- Archive: 351 regular members, 68,557,388 uncompressed bytes, 13,610,460 compressed bytes; SHA-256 `8c0470853ab9b577a36ef668a0daa98022598a04c1c2924b88b3ab73fcfd4d68`.
- Manifest SHA-256: `718ea7941228e9a71a53af13dcb4d6c1f409fd68ab55ca57851d0761d01809e8`.

Archive verification checked every member hash and consumed the full gzip stream through CRC/EOF. The independent acquisition audit additionally rechecked all 142 live and retained frozen inputs, exact argv/environment/cwd/raw-output hashes and parent/time associations for every child, source membership and independent inodes, both private and shared registry proofs, preserved indexes, and the download-lock release interval.
