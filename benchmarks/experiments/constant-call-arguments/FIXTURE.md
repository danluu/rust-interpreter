# Standalone compiler correctness fixture

Run nine original assertions with native Rust, the retained compiler/VM and the
folding compiler composed with that exact retained VM. Include original and
restored source, reject unused invalid borrow/type bodies (E0515/E0308), and verify
whole-artifact equality with the independent typed transformation. This is a
correctness run, without a timing gate or a claim about development speed.

Use two Cargo workers, offline dependencies, prepared isolated JIT tests, the
existing 10-million-instruction cap, standard memory/allocation limits and the
shared 45-second lock. The fixture has no Cargo dependencies and reuses the
installed standard MIR. The predecessor eight-test native target occupies
3,964 KiB; adding one scalar test does not create a large project build.

For this standalone qualification only, use the same explicit 7 GiB admission
as the host test build, checked before each child. This narrows the prototype's
blanket guest-export floor for this tiny fixture. Do not apply the exception to
fre, pgrust, Nu, Ruff, private projects or an actual-source-edit timing screen;
those retain their 8 GiB floor and separate cold-cache admission allowances.
Preserve raw receipts, all executed artifacts/catalogs and source restoration.
