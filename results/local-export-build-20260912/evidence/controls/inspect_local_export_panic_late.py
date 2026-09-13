"""Write root's explicit inspection of the already completed late-panic run.

This encodes the actual paths and argument derivation reviewed by root; it is
not a general symbolic verifier and launches no compiler or VM subprocess.
"""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[2]
B = Path(__file__).resolve().parent
RUN = ROOT / '.work/runs/local-export-panic-late-20260912-01'
FROZEN = B / 'local-export-panic-late-frozen.json'
PINNED = Path('/Users/danluu/.rustup/toolchains/nightly-2026-09-08-aarch64-apple-darwin/lib/rustlib/rustc-src/rust/compiler')
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

frozen = json.loads(FROZEN.read_text())
execution = json.loads((RUN / 'execution.json').read_text())
assert execution['status'] == 'awaiting structural inspection'
assert execution['completed_commands'] == 90
support = []
for relative, first, last in [
    ('rustc_middle/src/ty/mod.rs', 1830, 1872),
    ('rustc_mir_transform/src/lib.rs', 768, 823),
    ('rustc_mir_transform/src/pass_manager.rs', 384, 419),
]:
    path = PINNED / relative
    support.append(dict(path=str(path), sha256=sha(path), first_line=first,
        excerpt='\n'.join(path.read_text().splitlines()[first-1:last])))
assert 'self.optimized_mir(def)' in support[0]['excerpt']
assert 'RuntimePhase::Optimized' in support[1]['excerpt']
assert 'body.phase.name()' in support[2]['excerpt']

helper_prefix = [
    {'Local': {'dst': 0, 'offset': 0}},
    {'Load': {'dst': 1, 'address': 0, 'size': 8}},
    {'Local': {'dst': 2, 'offset': 8}},
    {'Load': {'dst': 3, 'address': 2, 'size': 8}},
    {'Unary': {'dst': 4, 'op': 'Not', 'src': 3, 'bits': 64}},
    {'Store': {'address': 1, 'src': 4, 'size': 8}},
]
signature = 'fn store_then_panic(_1: &mut u64, _2: u64) -> ! {'
assignment = '(*_1) = Not(copy _2);'
panic_call = '_3 = core::panicking::panic(const "panic-store late fixture") -> unwind continue;'
block = '    bb0: {\n        ' + assignment + '\n        ' + panic_call + '\n    }'
cases = []
for arm in ['baseline', 'candidate']:
    for inline in [False, True]:
        tag = arm + ('-inline' if inline else '-plain')
        artifact = RUN / tag / 'primary.rbc'
        jp = RUN / (tag + '-inspect.stdout')
        mir = RUN / tag / 'mir/panic_store_late_fixture.store_then_panic.3-3-000.runtime-optimized.after.mir'
        for path in [artifact, jp, mir]:
            assert sha(path) == execution['proofs'][str(path)]
        other = RUN / ('candidate' + ('-inline' if inline else '-plain')) / 'primary.rbc'
        assert artifact.read_bytes() == other.read_bytes()
        text = mir.read_text()
        assert text.startswith('// MIR for `store_then_panic` after runtime-optimized\n')
        assert signature in text and block in text and 'bb1:' not in text
        program = json.loads(jp.read_text())
        entry, helper = program['functions'][0], program['functions'][2]
        assert program['entry'] == 0 and entry['name'] == 'rust_interp_entry[]'
        assert helper['name'] == 'store_then_panic[]' and helper['frame_size'] == 16
        assert helper['args'] == [{'offset': 0, 'size': 8}, {'offset': 8, 'size': 8}]
        assert helper['code'][:6] == helper_prefix and len(helper['code']) == 7
        trap = helper['code'][6]
        assert trap == {'Trap': {'message': 'core::panicking::panic at ' + str(ROOT / 'tests/panic_store_late_fixture.rs') + ':10:5: 10:55'}}
        start = 39 if inline else 21
        assert entry['args'] == [{'offset': 8, 'size': 8}, {'offset': 16, 'size': 8}]
        assert entry['code'][9] == {'Switch': {'value': 22, 'cases': [[0, start]], 'otherwise': 10}}
        assert entry['code'][start:start+7] == [
            {'Local': {'dst': 17, 'offset': 40}},
            {'Local': {'dst': 18, 'offset': 24}},
            {'Store': {'address': 17, 'src': 18, 'size': 8}},
            {'Local': {'dst': 19, 'offset': 40}},
            {'Local': {'dst': 20, 'offset': 16}},
            {'Local': {'dst': 21, 'offset': 40}},
            {'Call': {'function': 2, 'args': [19, 20], 'destination': 21}},
        ]
        classifier = (B / 'owned-analysis-source/crates/mir-export/src/lower.rs'
                      if arm == 'baseline' else ROOT / 'crates/mir-export/src/lower.rs')
        assert sha(classifier) == frozen['proofs'][str(classifier)]
        classifier_text = classifier.read_text()
        assert 'let body = exporter.tcx.instance_mir(instance.def);' in classifier_text
        assert 'name.starts_with("core::panicking::")' in classifier_text
        trace = []
        entry_meanings = [
            'Initialize promoted boolean temporary r22 to zero; it is overwritten at PC8.',
            'r0 points to caller destination local at frame offset24.',
            'r1 points to the caller second-argument value buffer at offset16.',
            'Initialize caller destination from value. This Copy is not the witnessed complement Store.',
            'r3 points to caller first-argument mode buffer at offset8.',
            'Load the u64 mode into r4.',
            'Set r5 to zero for the mode comparison.',
            'Compare mode to zero; mode1 produces false, integer0, in r6.',
            'Copy the boolean comparison to r22 without changing false/zero.',
            f'For mode1, switch on zero to PC{start}; the normal-return branch is bypassed.',
        ]
        for pc, meaning in enumerate(entry_meanings):
            trace.append(dict(function_index=0, pc=pc, operation=entry['code'][pc], meaning=meaning))
        call_meanings = [
            'r17 addresses the caller reference-argument buffer at offset40.',
            'r18 is the address of the caller destination local at offset24.',
            'Store the destination address into the reference-argument buffer, not the complemented value into the destination.',
            'r19 addresses the initialized reference buffer at offset40.',
            'r20 addresses the unchanged caller value buffer at offset16.',
            'r21 provides a return buffer; the callee result has zero bytes and the callee traps.',
            'Call actual function2 with argument buffers r19/r20; its args copy eight bytes into frame offsets0/8 respectively.',
        ]
        for relative, meaning in enumerate(call_meanings):
            pc = start + relative
            trace.append(dict(function_index=0, pc=pc, operation=entry['code'][pc], meaning=meaning))
        helper_meanings = [
            'r0 addresses helper arg0 at offset0, containing the destination pointer copied from caller offset40.',
            'Load arg0 into r1: r1 is the address of caller destination local at offset24.',
            'r2 addresses helper arg1 at offset8, containing the value copied from caller offset16.',
            'Load the u64 value argument into r3.',
            'Compute the 64-bit complement of r3 into r4.',
            'Write r4 through r1 for eight bytes: the complemented value reaches the destination. No intervening operation overwrites r1 or r4.',
            'Trap for the directly recognized core panic at the original helper call span, immediately after Store.',
        ]
        for pc, meaning in enumerate(helper_meanings):
            trace.append(dict(function_index=2, pc=pc, operation=helper['code'][pc], meaning=meaning))
        cases.append(dict(arm=arm, inline=inline, artifact_sha256=sha(artifact), program_json_sha256=sha(jp),
            mir=dict(path=str(mir), sha256=sha(mir), function_signature=signature, block_excerpt=block,
                dereference_assignment=assignment, panic_call=panic_call, reachable_from_entry=True,
                same_basic_block=True, dereference_is_first_argument=True,
                stored_value_is_complement_of_second_argument=True, not_panic_preparation=True,
                terminator_is_recognized_original_fndef=True, is_actual_instance_mir_body=True,
                instance_mir_stage_reason='The selected helper is an ordinary local non-const function Item, not a constructor, always-const function, shim or virtual instance. Both frozen Lower::new implementations query instance_mir(instance.def). The installed pinned rustc_middle implementation routes this Item to optimized_mir. rustc_mir_transform returns the body after its Runtime(Optimized) phase; pass_manager dumps that phase as runtime-optimized/after. The actual dump has that header and exact helper signature. Diagnostic and primary artifact bytes match under otherwise identical flags.',
                recognized_definition='core::panicking::panic',
                classifier_source_reason='Pinned core/src/panicking.rs defines the public panic_internals-gated non-generic panic function with never return type in the same core crate as the panic_fmt lang item. The source calls that exact function directly. Both selected classifiers require Fn/AssocFn, the core/std lang-item crate and never return, then accept the core::panicking:: prefix. The assignment has a Deref projection and UnaryOp, so panic_preparation returns false; the whole-block early trap path cannot discard it. The retained actual Trap names that exact definition and helper span.',
                classifier_source_path=str(classifier), classifier_source_sha256=sha(classifier),
                reachability_reason='The helper has exactly one basic block, bb0, which is its entry block. The selected rust_interp_entry takes its nonzero-mode branch and calls this helper as actual bytecode function2 in both leaf configurations; the normal-return helper alone is inlined.',
                argument_mapping_reason='The signature binds _1 to &mut u64 destination and _2 to u64 value. The sole dereference assignment writes Not(copy _2) through _1, immediately before the direct panic terminator.'),
            bytecode=dict(function_index=2, function_name=helper['name'], unary_pc=4, store_pc=5, trap_pc=6,
                unary=helper['code'][4], store=helper['code'][5], trap=trap, reachable_from_entry=True,
                store_executes_before_trap=True, address_is_destination_argument=True,
                value_is_complement_of_value_argument=True, unary_source_is_value_argument=True,
                no_overwrite_between_unary_and_store=True, excludes_caller_initialization=True,
                argument_and_control_flow_derivation=f'Entry args are mode at offset8 and value at offset16. PCs1-3 initialize destination at offset24 from value. Mode1 follows PC9 to PC{start}. PCs{start}-{start+6} put the address of offset24 in the reference buffer at offset40 and call function2 with that buffer plus the value buffer. This call remains present with inlining enabled. Function2 args occupy offsets0 and8. Its PCs0-3 load destination into r1 and value into r3, PC4 computes Not64 into r4, PC5 stores r4 through r1, and PC6 traps. The helper has no branches or calls and no intervening writer; there is no path to its panic Trap bypassing Store5. Caller initialization and the reference-buffer Store are distinct operations and are not the witness.',
                trace=trace)))

report = dict(schema_version=1, coverage_pass=True, reviewer='root',
    method='explicit actual MIR and bytecode data-flow inspection',
    execution_sha256=sha(RUN / 'execution.json'), frozen_sha256=sha(FROZEN),
    fixture_sha256=sha(ROOT / 'tests/panic_store_late_fixture.rs'),
    source_support=support, report_writer_sha256=sha(Path(__file__)), cases=cases)
with (B / 'local-export-panic-late-inspection.json').open('x') as stream:
    json.dump(report, stream, indent=2)
    stream.write('\n')
print(json.dumps({'reviewed_cases': len(cases), 'coverage_pass': True,
    'inspection_sha256': sha(B / 'local-export-panic-late-inspection.json')}, indent=2))
