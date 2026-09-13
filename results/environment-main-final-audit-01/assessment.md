# Environment and capacity support with the combined compiler

The source/tool/evidence audit passes. The combined exporter and wrapper pass
98 tests per profile, 119 strict native/interpreter/JIT/cache/Cargo controls,
40 original/wrong/edit/restored project commands, and all 114 original pgrust
parser tests. Every project and full-parser bytecode artifact and catalog matches
the prior reference. Sources and assertions are unchanged or restored as
declared. Private raw commands and artifacts remain local.

Tool `b08f39e282ece70b125d23cf1a9b3a22cef5cfd4c03bf5b8cae023701f9b21ff`
retains the exact qualified environment VM `c55befb8`, whose earlier workspace
proof passes 484 tests per profile. Its changed exporter `fd636db6` and wrapper
`7ee7d2cc` include main's compiler selection and host-macro routing through
ca7318da. Both options keep their explicit defaults. Reused VM proofs are bound
to exact source and binary identity; the only bytecode source differences are
clarifying Rustdoc and a separately exercised ignored offline observer.

No new performance claim accompanies this integration. The earlier full-parser
edited comparisons still report15.78% slower wall under repository settings and
23.03% slower with matched incremental compilation. Those results describe their
recorded exporter/launcher composition, not arbitrary later main revisions.
Environment inputs remain immutable snapshots; C strings use checked bytecode;
all strict type and borrow checks finish before guest execution.

The audit preserves the earlier lock-admission failures. It also identifies the
prospective disk-admission paragraph added after the build/strict stages, verifies
the original plan bytes from their source commit, and verifies all actual source
and tool inputs. No completed guest command is repeated for this final audit.
