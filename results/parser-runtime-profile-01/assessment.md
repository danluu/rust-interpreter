# Full parser runtime attribution

One fresh invocation of the original C reference-vector test passes using the
qualified immutable VM and saved final-restored parser artifact. Existing
profiling and post-execution maps account for every emitted byte; the operation
map exactly reconstructs published code. The run executes 545,134,243 logical
operations: 540,302,783 native and 4,831,460 interpreted.

Only one executed function has no published native code:
`actions::<impl parse::Parser<'mcx>>::reduce_cold`, function 1357. Its 140,615
bytecode operations account for 4,547,956 interpreted operations in this run,
about 94.13% of the interpreted total. The fresh owner publishes 14,493,360 bytes
for 2,370 functions and reports one decline. Missing code alone does not identify
the decline reason; the following offline emitter result does.

This diagnostic changes profiling and JIT publication history relative to the
two-worker prepared-suite benchmark. It is not a command-time comparison, and
its counts are not retired host instructions. No compiler command or source
edit runs. An earlier 45-second shared-lock admission expired before any guest;
the completed admission executes exactly one guest command.
