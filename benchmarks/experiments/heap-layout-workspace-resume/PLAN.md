# Preserve passing workspace tests and complete only the VM build

Workspace01 passed all3 test commands (Python446pass22skip;Rust618pass13ignored in
both debug/release), then failed conservative disk admission BEFORE VM build.
Independently closed source/terminal/log evidence remains unchanged. Workspace02
rederives those test counts and exact commands, rechecks every frozen source,
and executes only the unstarted feature-enabled ordinary release VM build.
Retain the resulting VM/hash. No passing tests or guest commands are repeated.

Shared lock45s;2workers; fresh max(14GiB,8GiB+2*allocated shared target) before
compilation. The shared target is NEVER cleaned. Run only after new closed
compression provides sufficient fresh admission. Independently close finished
source/log/binary evidence before original guest profile01 or composition.
