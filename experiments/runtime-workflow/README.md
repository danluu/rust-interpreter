# Installed compiler workflow selection

The ordinary launcher accepts repeated `--rustflag=ARG` options for application
Cargo only. Standard-library setup/lookup, tool publication, and VM execution
keep their original environments. Ambient Cargo rustflags conflict with this
explicit option; arguments containing spaces retain their exact boundaries.

`bench_e2e_workflow.py` now accepts an installed `--runtime-compiler-key` in a
batched paired comparison with explicit baseline and candidate tool keys.
`--std-mir --std-mir-key KEY` selects the installed shared source-containing
standard library. Both modes validate the same runtime and std identities.
The native control keeps its separately declared compiler and profile.

Repeated `--guest-rustflag=ARG` arguments append to the existing MIR options.
`--baseline-guest-rustflag=ARG` replaces only the baseline's appended arguments;
otherwise both modes inherit them. For a compiler experiment, use explicit off
and on values, retain independent expected flags when verifying the result, and
keep the VM and exporter identical. Application-only flags are retained in the
launcher receipt and verified against the actual command and mode settings.

Use `--workload-lock /absolute/path/to/existing/benchmark.lock` with a bounded
`--lock-wait-seconds` when a checkout shares a benchmark host. The default lock
location remains workspace-local. Runtime selection currently requires normal
repository host profiles; it rejects `--build-tool-opt-level` before setup.

The focused controls cover clean std lookup, application/VM environment
separation, mismatched runtime/std identities, argument boundaries, independent
compiler flag expectations, the native check control, and legacy defaults.
They use synthetic children and histories. Application correctness and measured
latency require the separately built and qualified runtime tool composition.
