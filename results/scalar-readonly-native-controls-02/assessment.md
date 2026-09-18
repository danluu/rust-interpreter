The heap-aware native prototype passes all 359 bytecode library controls in
each profile, with 12 explicitly ignored diagnostics. The new heap-free control
covers tagged/untagged pointer boundaries and exact shared-arena reconstruction.
The emitter receives the same heap flag as the ordinary JIT prologue and does
not consult x7/x8 when they are outside the guest ABI.

The closure verifies 314 frozen bindings and four output artifacts against
`a97c5234`. The earlier passing 358-test run remains retained with its uncovered
ABI issue. No original-project guest or timing command runs. Main and installed
tools retain the qualified scratch/scalar runtime. Next measure actual native
admission and preserve existing scalar-body emission before candidate building,
strict/cache qualification, original profiles and the changed-source screen.
