# Saved-screen validator contracts

All seven mocked contracts passed. They cover exact workload selection, compiler/Cargo/tool and standard-library identity, physical compiler prefixes, per-arm cache history, preserved tests, malformed timing, and source-only Cargo comparison evidence. No real compiler, Cargo, VM, benchmark or holdout ran.

The first attempt exhausted its 600-second lock admission before starting tests. The second used a bounded 1800-second background admission. Both attempts, exact source versions, process receipt, test output and imported helper sources are retained in the archive; every archived member hash was verified.
