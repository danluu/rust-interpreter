# Current compiler with the measured guarded-local-facts VM

These are compatibility controls after the five-case 726-command campaign.
The immutable build must bind the exact measured VM to the current tested
exporter/wrapper; all previous VM/shared inputs stay exact. The new trap-remap
compiler controls have an explicit separate-target proof. No timing is repeated.

Run the two ignored compiler controls using the retained debug test executable,
stock pinned rustc, matching new exporter, original metadata std sysroot and
exact measured VM. Keep their original assertions, four path-remapping scopes,
uncalled type/borrow/const failures and restoration checks. Use the explicit
stock codegen-units setting. Record all 130 internal child commands.

Then run the existing 119 strict/cache/Cargo controls with the new tool and six
project-controller boundary tests. Qualify eight states in each of five real
projects: original, wrong edit, five valid edits and restored original. Compare
against the completed candidate history, retaining bytecode/catalog identity
observations and all original assertion outcomes. Project controls use the
existing conservative 13.27-GiB complete-cache admission estimate and per-case
floors. A separate full parser invocation covers all 114 original tests, reusing
the already retained native proof and executable.

Every workload holds the canonical lock, waits at most 45 seconds for admission,
uses at most two Cargo workers and checks eight GiB before children. These new
controllers live separately from the frozen build controller, so preparing them
does not mutate an ongoing build's inputs. Keep failure receipts and never repeat
successful commands after an interruption. All private source/command details
stay local. Report exact source, tool and artifact bindings on publication.
