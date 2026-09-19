# Preserve partial storage conversion and qualify exact creation-time copying

Compression01 stopped after132 verified replacements. Record133 is a successful
temporary copy whose creation time differs; its original remains intact. All241
remaining originals and the pending copy must be verified before continuation.
Do not rerun compression01 or overwrite its records, temporary file or terminal.

Read the local Darwin SDK attrlist declaration and installed getattrlist manual:
ATTR_CMN_CRTIME is a read/write timespec; returned attributes align to four bytes.
Use file-descriptor fgetattrlist/fsetattrlist to copy the exact seconds/nanoseconds
onto only a disposable fixture or a verified adjacent temporary copy. No setter
is applied to an existing evidence file. Test a distinct creation/modification
time fixture with subsecond values, preserve payload, mmap, mode, uid/gid, exact
mtime, and assert exact native creation-time roundtrip. Retain the earlier probe's
coverage limitation: it happened to give creation and modification the same time.

Qualify under the shared lock,12GiB initial/8GiB child, then independently close.
A later continuation consumes the immutable partial prefix, changes only the
uncompleted exact manifest entries, and keeps the original metadata obligations.
Neither compatibility qualification nor storage work changes performance gates.
