# Paired memory accesses: defer runtime work

The closed adopted captures contain7,192/8,228 structurally eligible64-bit
load/store pairs inside validated typed16-byte memory-data scopes. These could
remove28,768/32,912 emitted bytes before implementation-specific effects. Their
weighted executions are144,927,178/107,456,703; weighted words are not retired
instructions or a prediction of latency.

Only30/1,651 (1.82%) and13/1,439 (0.90%) sampled generated PCs belong to eligible
pairs. Those counts include both old instructions. Do not credit all affected
samples as eliminated time. There are zero ambiguous samples and no omitted
executed functions. Defer another narrow runtime prototype on this evidence.
The larger8-byte data-access bucket is not eligible for this local pairing rule.

Three decoder tests and four independent assembler controls passed. The initial
analysis failed on two meanings of the report field offset; the continuation
renamed the native PC field and retained all three successful control commands,
repeating no controls. No guest execution, code publication or runtime change
occurred. Historical source, input hashes and failed terminal are retained.

A read-only host check reports Apple M5 Max and hw.optional.arm.FEAT_CSSC=1,
but the existing operation attribution contains only one scalar CountOnes
sample in each capture; the exact profiles have only one interpreted Unary
operation each. Defer a CSSC/population-count candidate too.

The stronger next lead is CallIndirect: the exact profiles count1,025,947 and
843,776 interpreted indirect calls. In the block profile,948,377 occur at one
hashbrown::raw::RawTableInner::find_inner site. Across both profiles, native
Returns minus native Calls equals interpreted Call plus CallIndirect counts.
This suggests useful native-callee coverage but does not establish per-site
polymorphism, entry eligibility, compatible signatures or fast-path safety.
Inspect actual resolved targets and continuation coverage before designing a
bounded native indirect-call path. Preserve complete function-pointer/signature
validation, ABI copies, faults, budgets, cache limits and VM fallback.
