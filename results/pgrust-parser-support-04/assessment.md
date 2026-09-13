# Complete original SQL parser support

All 114 original `gram_core` tests from pgrust revision
`38d2517d3e09168a8fe222837730d435238ff358` pass in the custom JIT.
The exact native test set, source files and assertions are unchanged. This
includes the project's C reference vectors. It covers the parser library,
not the full database. Strict Rust type and borrow checks finish before execution.

The general boxed `FnOnce` receiver fix, coordinated 32,768-function capacity,
checked environment reads and bytecode-loop C string length lowering remove
the three successive blockers recorded in support runs 01–03. The compiler
exports 11,832 functions and 1,180,462 operations (29,458,018 byte artifact).
Environment values are actual process inputs, copied into read-only guest
storage; no missing-value stub or project-specific shim is used. Mutation,
unwinding and general foreign calls remain unsupported.

Tool `8c2d64bb756cbfedaaf84820cae1b1705575a7022326e239b04084f6217d06ae`
contains VM `c55befb8`, exporter `c66500d3` and wrapper `10fb7656`.
The workspace proof has 484 passing tests per profile; the subsequent
exporter-only change passes 89 tests per profile. The 119-command fixture and
strict Cargo qualification includes native environment bytes, cache identity,
invalid pointers/ABIs, edited/restored sources and uncalled type/borrow errors.

This support run executes one new complete custom command and reuses the
verified native 114-test proof. Both use two Cargo workers and the project's
line-table/unpacked/nonincremental profile; custom tests use two prepared
workers. All 4,918 frozen inputs verify afterward. The first admission timed out
on the shared lock without starting a parser command; its receipt is retained.

This is correctness and compatibility evidence, not a performance comparison.
Next measure complete edited-source build/test commands, explicitly separating
project-default and matched incremental profiles, with a wrong production edit
and source restoration. Existing workflow regressions remain qualification
work before publication of these experimental capacity/environment changes.
