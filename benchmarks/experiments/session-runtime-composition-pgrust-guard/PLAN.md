# Portable strict probes before pgrust timing

Attempt01 ended before any of the176 timing commands: the type probe correctly
produced E0308, while the borrow probe referred to std in the no_std hashfn crate
and produced E0433. Both servers consumed zero requests and closed normally;
source restoration and the complete failed-prefix evidence are independently
preserved. This is a controller fixture failure, not a performance measurement.

Use core::hint::black_box in the otherwise identical unreachable borrow probe.
Keep type/borrow errors E0308/E0499 mandatory before guest contact. Qualify both
probes in tiny std and no_std libraries with the exact pinned rustc metadata-only
error path: four rejections and no emitted code or metadata. Retain12 unchanged
accounting and six exact command controls, and freshly execute four source/outcome
controller controls plus four compiler probes (26 validated controls total with
18 retained and8 fresh). No workspace/shared-target build is involved;14GiB initial
admission for the small compiler probes,8GiB before every child, shared lock.

Attempt02 uses fresh compiler namespaces and endpoints. Every176-command state,
arm option, original hashfn test, strict requirement, artifact identity, session
CPU charge and full regression gate is unchanged. Require both closed fre passes,
the independently closed failed prefix, and the newly closed controller protocol.
Do not modify the earlier public controller or completed results. Later private
and parser admission must name the new closed pgrust02 result explicitly and
requalify their changed proof bindings. No runtime adoption or timing retry here.
