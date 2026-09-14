# Ordinary-region frame value coverage

The private-store and byte-phi whole-leaf prototypes failed their changed-source
primaries. Start from the adopted runtime, with all prototype runtime code absent.
Before designing ordinary-region SSA, measure available frame bytes and writes
overwritten within a bounded segment of each actual emitted region.

This test-only census starts with unknown registers and frame contents at every
region. It recognizes current-frame Local addresses, bounded unsigned 64-bit
constant offsets, and small Load/Store/Copy operations. Unknown memory, possible
integer division faults, assertions, transfers and unreviewed opcodes clear byte
availability. Copy reads precede overlapping writes. Register output aliasing and
complete extents are checked. At most 1,024 operations and 16,384 byte cells are
visited in one region. Memory-address facts are not seeded across entries.

Count each byte read with an earlier capture in the segment and each written byte
overwritten before its boundary. Join only complete-range opportunities to actual
remaining load_data/store_data instruction samples. Existing value forwarding
therefore receives no hypothetical payload credit. Retaining a captured value,
rematerialization, register pressure, frame publication and compile cost remain
unmodeled: these counts are coverage, not saved instructions or latency.

Reconstruct every ordinary function and scalar body from both adopted schema-2
captures exactly. No guest execution or executable publication. Run three new
alias/extent/barrier/overlap controls and four existing memory partition controls
in debug and release, plus two existing Python attribution controls. Preserve all
raw logs and source/input hashes, including failures. Global benchmark lock,
two Cargo/test workers, conservative build admission and 8 GiB child floor apply.

If coverage warrants a model, require differential full-state, fault and every-
budget controls before emission, strict checking and original-test profiles before
the fixed primary screen. A failed primary parks the candidate. No unchanged-build
or standalone-loop speedup claim and no automatic larger history.
