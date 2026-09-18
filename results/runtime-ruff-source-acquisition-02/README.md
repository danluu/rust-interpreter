The installed runtime now owns a fresh Ruff checkout at upstream commit
`d136bd8d002a648de5f344df602e492658306f1e`. The acquisition fetched local Git
objects, verified all 11,119 tracked entries (89,102,713 bytes), and wrote a new
ownership marker. The original checkout remained unchanged.

All 17 supervised Git commands passed. Independent readback checked both source
trees, their exact membership and file modes, distinct inodes, Git blob hashes,
and every command's arguments, environment, raw streams, process association,
and time bounds. Thirteen files have upstream CRLF checkout attributes; the
proof retains those attributes, normalized Git blob hashes, and exact checkout
byte hashes. The one relative symlink stays inside the checkout.

This is source acquisition evidence. It contains no application compilation,
runtime result, or edited-build timing claim. Native profiles and tests remain
the pinned upstream files.

| Evidence | SHA-256 |
| --- | --- |
| Acquisition receipt | `d4493e4564e23aef0d0f3bd89cc7799dd6855b1cdcf9dd0ca32308ba7c63880f` |
| Independent verification | `2eafb3da724027c0949dada074692d9731f91adc27f0fdbf71e3ce4118d373f0` |
| Archive | `b4ddaf579aad2f904fe8b27b2aa2c892c15e4ecda11e41d29cbcafb070924f6e` |
| Archive manifest | `ab1474d616b7d61dd7aa64095d0c46e782933ac02fd74f7df3cd8c4029a96f39` |

The 9,379,519-byte archive retains 94 logical proof members, including both
proposals, frozen inputs, source inventory, raw command evidence, and independent
verifier. All member hashes and the complete gzip trailer/CRC passed readback.
The original proposal was never launched. Proposal 02 adds fresh-destination
checks after admission and immediately before Git initialization, plus 9 GiB
scan and copy guards. It ran once under the canonical workload lock with a
600-second wait, 16 GiB entry gate, 9 GiB active stop, and 8 GiB running floor.

Archive member names preserve the original absolute proof paths without their
leading slash. The source controller is retained at
`experiments/runtime-application-admission/ruff-acquisition-02/acquire_ruff.py`;
its exact plan, launch, and input freeze are in the archive. The live application
checkout and its Git objects are not duplicated in the evidence archive.
