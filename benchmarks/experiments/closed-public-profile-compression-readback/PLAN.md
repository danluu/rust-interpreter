# Retain allocation drift and re-read unchanged compressed evidence

Compression01 finished successfully for all176 files. Its original independent
closure first failed lock admission; a second supervised readback failed its
whole-stat-tuple equality check. Read-only inspection found nine files with lower
st_blocks and every other recorded identity field unchanged. This is an observed
allocation change, not yet an explanation of the filesystem's internal behavior.

Preserve both failures, the original controller/closure sources, summary, records,
and all files. Re-read every normal/mmap SHA, exact native creation time, and
preserved metadata. Require the same inode, device, ctime and compression flags as
the successful controller recorded, too. Permit only positive, nonincreasing
allocated block counts, recorded individually in final-readback.json. Any other
change fails. No compression command, replacement or unlink runs in this step.

Bind the new reader's Git source separately from the original frozen source and
bind the failed reader's finished receipt and log. Keep the summary's original
allocation snapshot intact; the closure additionally reports current allocation.
Hold the shared benchmark lock45s and require8GiB. No performance claim follows.
