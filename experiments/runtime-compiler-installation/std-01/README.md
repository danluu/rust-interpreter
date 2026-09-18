# Installed runtime standard-library setup

This proposal invokes the ordinary `scripts/std_mir_source_paths.py` CLI with
`--runtime-compiler-key eca3d1317ba4c852d64de435aa0f0e5d87ae63bd4eb96cfafacc7b0a85841d03`
from the installed runtime's existing owner. The explicit shared source-paths-v2
namespace permits later comparison arms to select one identical prepared std
sysroot. It does not relabel a complete stage2 compiler or claim an application
benchmark result.

`plan.json` specifies the exact command and complete environment. Cargo remains
the pinned nightly-2026-09-08 executable implementing commit 3c0b5347's reviewed
root-dir/trim-paths recipe. Network access is disabled for Cargo and the rustup
distribution route is unusable. DEVELOPER_DIR fixes the Xcode tool selection;
the system inspector, selected inspector, proxy, Cargo and Python bytes/routes
are guarded before and after setup. All fourteen possible ancestor/home Cargo
configurations are guarded, including their absence.

The wrapper retains its frozen sources and proof inputs, then supervises the
ordinary CLI with the existing task-owned process monitor. The CLI acquires the
canonical benchmark lock and its owner-local std lock with 600-second waits.
The wrapper deliberately does not hold a second canonical descriptor. Entry
requires 16 GiB free; active task-owned groups retain the existing 9 GiB stop
and 8 GiB running floor. Input retention is capped at 64 MiB total and 32 MiB
per file. The two source copies total 144,560,290 bytes; generated metadata and
Cargo output are additional. These free-space gates are not a disk reservation.

Seven direct CLI children are expected: Cargo location and version, two Cargo
Mach-O inspections, native E0080 source probe, the ordinary two-job std metadata
build, and the prepared E0080 source probe. Cargo's compiler children remain
ordinary build work and are not misreported as seven total operating-system
processes. Existing output keys or run directories are rejected; a failed
attempt and every completed receipt remain in place, without automatic retry.

After success, the wrapper reloads the immutable output with full content
rehashing and verifies the actual command labels and return codes. The std
key is derived from actual Cargo/platform/configuration evidence during setup,
not guessed before those probes. Readiness explicitly leaves full diagnostic
presentation and application integration unqualified. No application or
holdout benchmark is inspected or executed by this setup.
