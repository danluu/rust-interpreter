# Superseded, unrun prototype

Do not compile or adopt this version. Source review identified an unresolved
pointer-provenance concern when moving `Arena`: its nested, directly owned
retained `Box` can move while cursor pointers derived before that move remain
stored in the arena. Putting the box inside `RefCell<Storage>` addresses the
predecessor's interior-mutability problem but does not establish this additional
movement property. No execution or performance claim supports this version.

All existing version 02 files remain unchanged. The fresh
`../proc-macro-arena-reuse-03` successor keeps the original
`RefCell<Vec<Box<[MaybeUninit<u8>]>>>` layout, leaves the original growth and
allocation/write functions unchanged, and adds an actual-code move regression.
That successor is separately subject to source review and tests.
