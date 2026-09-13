# Retire completed Nushell compiler intermediates

The rejected scalar-Copy campaign completed all 726 commands and its final
source/input audit. This cleanup targets only its completed 132-command
Nushell case: three custom namespaces and three native targets. Controller
receipts, source ownership, exact paths, open files and each removed file's
identity were checked under the shared and namespace locks.

All 28,509 protected hashes remain unchanged. The 180,563 eligible compiler
intermediates held 39,626,503,484 logical bytes; observed free space rose from
15,540,350,976 to 35,262,050,304 bytes. APFS sharing and concurrent external
activity prevent treating logical bytes as physical reclamation. Sources,
executables, bytecode, catalogs, saved timings and installed tools remain.
No private or other-session cache was selected. This is a completed one-shot
cleanup, with no process control or autonomous cleaner added.
