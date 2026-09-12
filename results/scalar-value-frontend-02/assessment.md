Real strict MIR export qualification passes 424 commands, including 360 custom
VM executions compared with native Rust. Five sources cover private scalar
calls/recursion/borrows, aggregate relocation, tracked callers, scalar constants
and coercions. Each runs with ordinary and enlarged MIR optimization, with
scalar promotion disabled/enabled, through interpreter, ordinary JIT and
resumable JIT with persistent registers. Original fixture assertions remain.

All ten flag-off artifacts match the retained production exporter byte for
byte. All ten scalar exports carry version 6, pass typed artifact inspection,
and reconcile emitted CallValue counts with compiler reports. No proof bounds
were exhausted. The purpose-built ordinary fixture promotes 15 formal inputs,
10 results and 16 call sites; pointer-storage inputs are admitted while a
projected struct input is rejected. The enlarged fixture still executes recursive
value calls. Existing coercion fixtures carry identities through 76 ordinary
and 46 enlarged aggregate relocations.

Uncalled type errors, uncalled borrow errors and the scalar/demand combination
all reject before artifact publication. The first inspector-build failure is
preserved separately. Tool aa56492e192ef2e87f69ed417b34c8f717b28c31a0fa67f5d63fbb92f313c9cd
is unchanged from the 334-test compiler qualification.

This is correctness qualification, not a performance measurement. Cargo flag
changes, audit packs, traces, real workload assertions and the original fresh
end-to-end gates remain. The experiment launcher now discovers the shared
launcher support modules when invoked outside the root scripts directory.
