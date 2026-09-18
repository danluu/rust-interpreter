# Reduce stock launcher startup overhead

Ordinary stock launches now validate compiler/tool association through a small
shared module and import the custom compiler implementation only when an explicit
compiler key needs it. The validation functions were relocated without changing
logic or error ordering. Existing custom_compiler exports remain compatible, and
the workflow input inventory includes the new module.

The fixed startup screen measured **9.4776% lower component CPU**, using the
geometric mean of twelve paired candidate/baseline ratios. Component CPU medians
were **15.902 ms → 14.367 ms**. The clock includes importing interpreter and one
successful real interpreter.main call with --inline-leaves, installed-tool byte
hashing, capability/association checks and owned workspace creation.

| Metric | Paired reduction | Candidate wins |
| --- | ---: | ---: |
| Component CPU | 9.4776% | 12/12 |
| Component wall | 9.4384% | 12/12 |
| Whole probe-process CPU | 4.4378% | 12/12 |
| Whole probe-process wall | 3.6608% | 12/12 |
| Whole probe-process peak RSS | 3.1112% | 12/12 |

Cargo and VM execution were stubbed at their subprocess boundaries; unexpected
process launches were rejected. Tool binaries were checked but not executed. The
sidecar is a marked stub, not validated bytecode. These measurements establish
launcher component/probe-process improvements, not complete Cargo builds, MIR
exports, guest execution, custom compiler routes or unknown holdout performance.

Four prescribed warmups populated one private Python cache. Twelve subsequent
AB/BA pairs used fresh processes and -B without changing its 68 files, 1,899,299
bytes or 28 directories. This is a warm-cache screen. All eight preregistered
gates passed; both order strata improved; every sample was retained. Whole-process
wait4 CPU/wall/RSS include driver setup and provenance reporting outside the
component clocks. Transitive macOS shared libraries were not fully inventoried.

All **81 Python correctness tests passed**, with no skips/failures. They cover
association guards/error order, the stock import boundary, custom compiler/Cargo
and runtime routing, std source paths, tool caching and launcher metric boundaries.
Independent raw audits checked the startup screen's 28 reports/56 child records,
inputs/cache/dependencies and recomputed gates, and the unit suite's 16 children
and source bindings. No workload was rerun while assembling this packet.

summary.json contains every sample, all 56 startup child records, all 28 parsed
raw reports, the unit suite result, frozen decision/metrics and original absolute
paths/hashes. Repeated raw report fields are factored into shared_raw_report_fields;
merging them back reproduces each original report exactly. File proofs are stored
once in supporting_original_files. The original result SHA-256 values are:

- Startup: 6f0a333a8caab65febdf5f3a5f18d8203a0527af522485aab9b29328fb700914
- Units: 2da23207fbb7896cbe471b584f8308c09617055dcda1ae29e5639b07bd1a0c28

The driver, executed controllers, protocol, decision, manifests and six-file patch
are copied byte-for-byte. Absolute paths preserve provenance; reproduction on
another checkout requires new owned output paths and rebound inputs. Existing
attempts must not be reused. PROTOCOL.md describes its pre-execution draft stage;
the copied final run-screen.py has the completed 81-test qualification hash bound.
No production source, existing evidence, cache or process was changed by assembly.


## Compact record layout

Join each startup_rows entry with startup_children by label; the row adds arm,
pair, warmup and component timings to the child receipt. Child terminal_file is
an added provenance reference. Child logs map stdout/stderr to original paths;
supporting_original_files supplies their byte counts and hashes. The referenced
terminal JSON preserves the remaining receipt fields. Startup result log proofs
were added after terminal-file publication, so those files do not contain logs.

qualification retains suite outcomes, inventory and child records. Its input_files
references the shared file proofs; bindings_before_after_identical records the
checked equality. Full original filesystem stamps and before/after dictionaries
remain in the hash-bound original unit result, rather than being repeated here.

For exact report values, merge shared_raw_report_fields[shared_fields] with each
raw_startup_reports entry's report. For comparison with the raw metric summary,
remove percent_reduction from each metric: it is the derived value
100 × (1 − geometric_mean_ratio). No measured value was altered by this layout.
