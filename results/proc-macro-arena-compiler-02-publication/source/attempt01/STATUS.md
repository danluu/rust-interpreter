The fixture and exact 20-command plan are independently source-reviewed and
remain uncompiled. X's review is
`.work/proc-macro-arena-compiler01-independent-source-review-01.json`, SHA
`7c376be3ac20fbf026f15c7eab2bc1f124218ab7ebd9aa8508b86ebbe0095240`.

After that fixture review, `run_once.py` was added as a separate one-shot runner
draft at the parent's request. The README's original statement that no wrapper
had been added describes the preceding fixture-only handoff. The runner remains
unrun and awaits root source review; it does not create a reusable framework.

`runner-source-review.json` records the bounded static review and a metadata-only
census: 101 explicitly named input files, 386,749,146 bytes. This includes the
installed std component manifest's named files, the exact rustc/driver/LLVM
files, previous library source provenance, selected client libraries and fixture
sources. No binary payload was reread during that census. The runner will read
and hash the selected inputs under canonical ownership and recheck them after
all children; those current hashes and all actual outcomes are still absent.

The runner retains exact per-child commands, PID/parent/time/limits/raw records,
continues bounded waiting after observation errors, and records actual closure
before hashing outputs. A timeout preserves an explicit potentially-live child;
the runner sends no signals and starts no further child. It retains full JSON
diagnostics and rejects unexpected spanless errors, allowing only the exact
abort summary whose error count matches the retained primary diagnostics.
The stock/candidate comparison uses stable fields and checks each macro dylib
before and after every caller. No result or performance claim exists yet.
