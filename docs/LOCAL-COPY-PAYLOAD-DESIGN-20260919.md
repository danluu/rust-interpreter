# Reserved payload registers for local copies: conditional prototype

Status: design only. The first saved-load census attempt stopped at the shared
lock without analyzing data. Do not implement or benchmark this proposal merely
because the register bookkeeping is straightforward. Require useful actual-load
coverage from the registered continuation first.

The existing local-copy path can emit three instructions for an aligned eight-
byte frame-to-frame copy: form the frame base, load through x9, store through x9.
Its adopted scratch cache retains bytes only while x9 still holds them. This
proposal gives selected memory values separate temporary storage, rather than
enlarging the virtual-register allocator or extending the old scratch-width rule.

Reserve d17 through d24 within one native region. On a miss, use ldr dN / str dN
in place of the existing scalar payload load/store; this requires no extra move.
On a hit, store the resident dN value. Guest memory remains fully committed after
every operation. No delayed store, frame virtualization, modified bytecode,
changed logical instruction count, or cross-region entry state is required.
This does not predict latency: vector accesses, compile-time analysis, changing
scratch reuse and code placement can erase the instruction saving.

Use actual typed emitter facts for both complete in-frame ranges. Start with
aligned eight-byte copies that otherwise use the ordinary scalar load/store path;
retain existing constant/register forwarding and x9 reuse where they apply.
Use a fixed bank of eight payloads and at most four exact local aliases per value.
Eviction discards facts without spilling because guest memory is current.

Read/capture the entire source before destination invalidation or stores.
Overlapping writes kill every affected alias, including an old source alias.
Then attach the destination range to the selected value. A payload with no known
aliases is immediately reusable. Unknown writes, calls and unreviewed effects
discard all facts; the first prototype may conservatively discard on every
Store/nonmatching Copy too, matching the diagnostic model. A region boundary
starts empty, including linked native entries and interpreter re-entry.

The most important integration detail is x9 validity. The current Copy path
unconditionally records the destination as holding x9's payload. A vector copy
does not establish that fact. Its completion must skip that capture and retain
only earlier x9 facts that survived the real emitted words and memory aliases.
Likewise it must not attach a stale virtual-register value to the destination.
Existing guarded-range d16, guest persistent GPR pairs and bounded memmove
v0..v7 must retain their current meanings. Audit every admitted operation and
out-of-line path for d17..d24 writes; the proposed allocation is not an ABI proof.

Before any performance screen:

1. Restore the adopted Rust baseline on a new owned experiment branch, retaining
   all compiler/diagnostic work and the parked switch sources in history.
2. Add the bounded typed state and effect handling with a disabled/reference
   mode. Demonstrate alias invalidation, capacity eviction, same-address copies,
   overlaps, skipped x9 capture, constant forwarding and arbitrary VM re-entry.
3. Verify emitted load/store encodings independently and exercise native ABI
   preservation, interpreter/JIT memory equality, every relevant budget boundary,
   invalid addresses, loops, calls and capacity fallback in debug and release.
4. Reconstruct the complete adopted saved arenas exactly before interpreting
   diagnostic changes. Preserve original function/PC identities and counters;
   include all new admission and compile costs. Check the real original suites
   and strict type/borrow rejection before installing a content-addressed tool.
5. Use the existing ordinary-VM complete-edit primary and its independently
   qualified accounting. Reject an unsuccessful primary without unchanged
   retiming. A pass only admits the full public/private/parser/Nushell guard
   sequence; it is not automatic runtime adoption.

Builds remain subject to dynamic disk admission and the shared benchmark lock.
Any necessary retirement is confined to exact, independently closed task-owned
compiler namespaces, with protected evidence/binary hashes and fresh open-file
checks. The shared build target and other sessions remain out of scope.
