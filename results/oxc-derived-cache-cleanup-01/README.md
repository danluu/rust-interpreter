# Completed Oxc derived-cache cleanup

Two completed caches created for this task were removed after their complete histories and retained evidence were independently verified. This recovered capacity for the separately reviewed strict Oxc qualification without lowering its 24 GiB entry gate.

| Exact directory below the Oxc experiment owner | Removed entries, including root | Result |
| --- | ---: | --- |
| `.work/oxc-runtime-compatibility-01/cache` | 5,615 | Passed |
| `.work/oxc-native-compatibility-02/target` | 4,592 | Passed |

Before each removal, the controller checked the exact frozen membership and device/inode/mode/link-count/size/mtime/ctime of every entry. Both trees contained only regular files and directories; all hardlink names were accounted for inside the respective deletion root. The controller held the canonical lock, required an empty open-handle check, checked recorded process IDs and start times, then unlinked only admitted names and removed empty directories from the bottom up. It followed no symlink. Allocation blocks were recorded as observations because filesystem block accounting changed without any identity/content-related stamp change.

The native executable was first copied to an independent inode outside the target and preserved in the [verified executable supplement](../oxc-native-final-executable-02/README.md). All runtime bytecode, catalogs, call reports, compiler records, raw output and receipts remained outside the cleanup root and matched the prior archive before and after cleanup. Source checkouts, private/shared registries, compiler toolchains and installed runtime artifacts were outside both deletion roots.

Both stages used 600-second canonical admission and a 9 GiB cleanup safety floor, with the supervisor's 8 GiB floor unchanged. The strict workload retained its separate 24/9/8 GiB gates. Final recorded free space after native cleanup was 26,099,576,832 bytes. Each cleanup had exactly two read-only child commands, both returning 1 with empty output because no open handles or original process IDs remained.

The independent audits reconciled exact deletion-ledger membership/order, both raw child receipts and output hashes, parent/time associations, frozen inputs and preserved evidence. Native retention additionally rechecked the exact 107,592,208-byte executable outside its removed target.

- Runtime terminal SHA-256: `e5092667cf18f302bc04bfbb2e53787a63d13b2c83b5c6b262eb418632b5b881`; independent audit `be07908d45d8d5e3c5d8dab4246133300899eb186f67fd8d09989b4eb5bd1a3a`.
- Native terminal SHA-256: `1c3fc6c7002b04f10caa27b530650ba35160c9e6969b0a842cb1bbcba7ba1eb7`; independent audit `6de90a82b365867d1125dcc08c0994e6d4fa08b89871ee9a0269b18d884dcea5`.
- Archive: 46 regular members, 13,359,120 uncompressed bytes, 1,009,852 compressed bytes; SHA-256 `afbdcd41051cc50c7cfb27e056d6a0fc7d879c45e2af559205a92a5134924591`.
- Manifest SHA-256: `3ab1460a18b4f068c63aca3986234040a19e0b2b05abce027d4cda851a0c476a`.

The archive contains both exact plans/freezes, helpers, assessments, admitted inventories, process/handle probes, supervisors, terminal receipts, deletion ledgers and independent audit results. Previously committed compatibility/executable archives and executor binaries are referenced by frozen hashes rather than duplicated. Every member and full gzip CRC/EOF were verified. No compiler or application benchmark was run by these cleanup stages.
