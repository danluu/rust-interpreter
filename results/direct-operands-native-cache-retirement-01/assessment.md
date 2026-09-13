# Completed public cache retirement

Retired only non-executable compiler intermediates in the completed Nushell native/native-line-tables/check caches, after terminal ownership and open-file checks under the shared lock. Source, bytecode, installed tools, executables, dynamic libraries, private caches and unrelated workloads were preserved. All777 protected hashes remain unchanged.

Removed146639 files (26,895,576,319 logical bytes). Observed free space rose from16,316,715,008 to27,785,306,112 bytes, about10.68GiB reclaimed; logical file sizes overstate physical reclamation. Detailed inventories and process/open-file receipts remain local. This is storage maintenance, not optimization evidence.
