# Scalar ABI artifact contract qualification

The isolated format/validation implementation passes 297 debug and release workspace tests, one ignored. Eight new tests cover exact legacy serialization, explicit scalar metadata, versions/trailing data, arity/register aliases, widths/upper bits, ordinary structural validation and metadata bounds.

Both original real artifacts decode and re-encode byte-for-byte: folded has 1,048 functions, token 5,421. Version 5 retains its original wire format; version 6 appends a dense scalar ABI table. Existing execution entry points reject version-6 bodies. Scalar metadata uses explicit registers and frame-slot alternatives, with no pointer/offset tagging.

This milestone implements the artifact contract only. No scalar guest has executed and no runtime tool was published. The [next step](../../benchmarks/experiments/scalar-value-abi/INTERPRETER-NEXT.md) reuses the custom VM loop for scalar input/result locations, indirect calls and TLS. Native resumable support, caller value operands and compiler promotion remain required before performance comparison.

[Exact source, commands and tests](summary.json); [terminal execution receipt](execution.json).
