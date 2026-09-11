# Broad candidate native differential validation

Both default and leaf-inline modes pass all 47,004 recorded commands, including 22,238 interpreter and 22,238 JIT invocations. The existing assertions and strict rejection cases are unchanged; tool 9637 retains the exact 0e VM/wrapper and changes only the isolated exporter. This is broad existing fixture coverage, not complete Rust or libtest support. Exact sources, binaries and subprocess records are bound in summary.json and execution.json.
