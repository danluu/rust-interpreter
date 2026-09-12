Qualify serialized scalar programs through every supported CLI engine mode.
Use exact qualified native-build-03 source, changing only the fixture writer to
add an identity cast: the resulting three-operation native region exceeds the
ordinary emitter minimum and must execute three instructions in generated code.
The fourth instruction is root Return. This prevents interpreter fallback from
masquerading as a native CLI success.

Run 64 commands: native Rust control, six legacy cases, fifteen scalar cases,
five per-PC profiles, thirty budget boundaries, and four malformed/unsupported
input checks, including build and fixture generation. Require 21 successful
engine cases, exact outputs for zero/ordinary/wrapping inputs, three native
instructions in each JIT success and one hit at every PC in each profile. Retain
explicit tree/stub rejection. Reuse no guest state across processes.

The underlying library passed 310 debug/release tests; the CLI and runtime source
remain byte-identical to that source. Do not repeat unchanged library tests.
Freeze every input, binary, artifact and command. Use the nonblocking benchmark
lock, require 9 GiB for this small CLI build and preserve the 8 GiB floor.
No performance measurement or runtime publication. Caller value operands and
compiler promotion still precede the real-workflow decision.
