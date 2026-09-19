# Selective normalization of implicit-zero registers

Status: the closed typed census admits a new prototype. The conservative
implicit-zero runtime remains parked after its failed primary, and main retains
the adopted VM. This proposal changes interpreter repair work; it does not
repeat the old candidate with another timing run.

The original prototype restores every proven-narrow read before interpreting
an operation. Some VM consumers first cast to usize/u8, mask integer operands,
or write only the low eight bytes. Their result cannot depend on physical upper
bits, so normalization is unnecessary. Aliased roles must still count: a register
used both as an address and a wide Store payload needs normalization for the
payload, and an indirect handle needs normalization even when it is also an
argument address.

Move the tested role visitor into the production width module and use it for
repair. Keep unknown and unreviewed consumers full-width. In particular, checked
indirect handles, TLS arguments, C allocation wrappers, descriptor helpers,
full truth/selection and128-bit arithmetic retain their required repairs.
Do not relax handle validation or change logical values, working-memory budgets,
initialization, borrow/type checks, fault order or instruction profiles.

The census counts6,542,145→1,033,563 repairs in block and8,513,802→843,810 in
exhaustive token. Almost all remaining work is checked indirect handles. Native
emission and proof/storage admission remain exactly the same as tool3e53b127.
Compare generated code with that retained prototype during original-profile
qualification, and continue using adopted df4006e0 as the performance baseline.

Add native-to-interpreter heap fallback cases with real reused wide backing,
followed by a full-width consumer, and a direct repair test that verifies low-only
reads leave physical high bytes intact while a later full read normalizes them.
Retain all poison, persistent reload, metadata, TLS, indirect, ABI, budget and
fault controls. Full workspace,121strict/cache commands, exact original profiles
and the unchanged40-command primary precede any larger comparison or adoption.
