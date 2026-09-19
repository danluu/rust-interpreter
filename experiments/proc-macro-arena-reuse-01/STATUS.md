# Rejected unrun predecessor

This prototype is rejected for its retained-storage representation. Do not
compile, benchmark or adopt it. Its original patch, source copies and metadata
remain unchanged as history; none was executed.

The retained `Box` was outside the arena's `RefCell`, although allocations write
through raw pointers under `&Arena`. Rust's shared-reference immutability rules
cover transitively reachable boxed bytes; the original interior-mutability
boundary therefore did not cover the retained page. See the
[Rust Reference](https://doc.rust-lang.org/reference/behavior-considered-undefined.html#undefined.immutable)
and [UnsafeCell rules](https://doc.rust-lang.org/std/cell/struct.UnsafeCell.html#aliasing-rules).

The separate [source-only successor](../proc-macro-arena-reuse-02/README.md)
places both allocation owners inside one `RefCell<Storage>`. It remains unrun
and requires independent source review. No performance benefit is established.
