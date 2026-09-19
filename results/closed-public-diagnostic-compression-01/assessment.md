# Closed diagnostics preserved with lower allocation

All22 selected JSON files in ten explicitly named closed public diagnostic runs
retain exact normal-read/mmap hashes, ownership, mode, mtime and native creation
time. Independent readback also verifies each replacement's inode and ctime;
only positive, nonincreasing allocated block counts are permitted.

Allocation decreased from1,349,488,640 to168,046,592 bytes:1,181,442,048 bytes
(1.10 GiB). No evidence was deleted, and no private/peer data, shared build target,
source or installed tool was selected. No guest command or timing ran. This
provided reserve for the previously unstarted standalone VM build.
