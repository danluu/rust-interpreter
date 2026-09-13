# Environment input in the custom engine

The experimental environment-capable tool supports Rust `std::env::var` and
`var_os` through checked C `getenv` lowering. Values come from the VM process's
actual environment, including empty values and Unix non-UTF8 bytes. An absent
name returns null. C string length runs through ordinary checked bytecode loads,
with instruction and memory limits; it never dereferences a host pointer.

The execution owner captures one immutable snapshot if the program contains an
environment read. A prepared worker retains that snapshot across its entries.
Each entry gets fresh read-only guest copies of the values alongside its fresh
memory, globals, heap and TLS. Repeated reads of a binding return the same guest
pointer within that invocation. A new owner captures current process inputs.
Code caches and exported artifacts do not contain the runtime environment.

Imported value bytes and a bounded allowance for the lookup index count against
the guest memory limit. Writes and ordinary frees cannot modify those values.
Guest environment mutation, enumeration and concurrent host mutation are outside
this contract. A supported environment read does not imply support for a later
backtrace, unwind, file operation or arbitrary foreign call.

The opcode is appended to the bytecode format, preserving existing opcode
encodings. New artifacts require an engine that understands it. The exporter
accepts the pinned C pointer signatures and rejects incompatible declarations.
Type and borrow checking still complete before guest execution.

The [114-test parser proof](../results/pgrust-parser-support-04/assessment.md)
uses these general mechanisms without changing application sources or assertions.
The associated workspace, native-environment and strict-cache qualifications are
correctness evidence. Edited-source comparisons determine development latency;
support-build durations do not establish a speedup. Capacity/environment changes
remain experimental pending the existing-project regression work.
