"""Current integrated compiler evidence for the generated status page."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def render():
    paths = [f'results/{run}/summary.json' for run in (
        'aggregate-integration-root-01', 'aggregate-relocation-e2e-01',
        'aggregate-relocation-heldout-recovery-01', 'budget-register-primary-01',
        'call-slot-primary-01', 'whole-call-build-02', 'whole-call-fixtures-01',
        'whole-call-export-smoke-02', 'whole-call-primary-02', 'whole-call-costs-01',
        'scalar-boundary-build-02', 'scalar-boundary-export-smoke-02', 'scalar-boundary-census-01',
        'scalar-boundary-admission-01', 'scalar-abi-artifact-build-01',
        'scalar-abi-interpreter-build-01', 'scalar-abi-cli-01',
        'scalar-abi-native-build-03', 'scalar-abi-native-cli-01', 'scalar-value-calls-build-02')]
    (integration, primary, held, budget, slots, whole, fixtures, smoke, whole_primary,
        whole_costs, scalar_build, scalar_export, scalar_census, scalar_admission,
        scalar_artifact, scalar_interpreter, scalar_cli, scalar_native, scalar_native_cli, caller_values) = [json.loads((ROOT / p).read_text()) for p in paths]
    key = integration['tool_key']
    if not (all(d['status'] == 'passed' for d in (integration, primary, budget))
            and held['status'] == 'all seven histories verified'
            and integration['component_identity_matches']
            and integration['actual_binaries'] == integration['expected_binaries']
            and primary['expected_tools']['candidate']['tool_key'] == key
            and primary['primary_performance_gates_passed']
            and held['heldout_gates_passed']
            and not budget['primary_gates_passed']
            and slots['status'] == 'passed' and not slots['primary_gates_passed']
            and all(d['status'] == 'passed' and d['tool_key'] == whole['tool_key'] for d in (whole, fixtures, smoke))
            and whole['tests']['debug']['passed'] == whole['tests']['release']['passed'] == 300
            and fixtures['vm_executions'] == 1024 and fixtures['strict_rejections'] == 2
            and whole_primary['status'] == whole_costs['status'] == 'passed'
            and not whole_primary['primary_gates_passed']
            and all(d['status']=='passed' for d in (scalar_build,scalar_export,scalar_census))
            and scalar_build['exporter_test_count']==45 and scalar_census['tests_passed']==5
            and scalar_census['tool_key']==key
            and scalar_build['tool_key']==scalar_export['tool_key']==scalar_census['observed_tool_key']
            and len(scalar_export['cases'])==len(scalar_census['cases'])==2
            and all(c['bytecode_identical'] and c['original_assertions_pass'] for c in scalar_export['cases'])
            and scalar_admission['status']=='passed' and scalar_admission['tests_passed']==11
            and scalar_artifact['status']=='passed' and not scalar_artifact['runtime_published']
            and scalar_artifact['tests']['debug']['passed']==scalar_artifact['tests']['release']['passed']==297
            and scalar_interpreter['status']==scalar_cli['status']=='passed'
            and scalar_interpreter['tests']['debug']['passed']==scalar_interpreter['tests']['release']['passed']==305
            and len(scalar_cli['commands'])==23 and scalar_cli['successful_engine_cases']==9
            and scalar_cli['parent_tool_key']==scalar_interpreter['tool_key']
            and not scalar_cli['runtime_published']
            and scalar_native['status']==scalar_native_cli['status']=='passed'
            and scalar_native['tests']['debug']['passed']==scalar_native['tests']['release']['passed']==310
            and len(scalar_native_cli['commands'])==64 and scalar_native_cli['successful_engine_cases']==21
            and scalar_native_cli['parent_tool_key']==scalar_native['tool_key']
            and scalar_native_cli['native_modes']==4 and scalar_native_cli['native_instructions_per_success']==3
            and not scalar_native_cli['runtime_published']
            and caller_values['status']=='passed' and not caller_values['runtime_published']
            and caller_values['parent_tool_key']==scalar_native['tool_key']
            and caller_values['tests']['debug']['passed']==caller_values['tests']['release']['passed']==319
            and caller_values['caller_value_tests']==8):
        raise RuntimeError('integrated compiler evidence differs from the recorded decision')
    index = json.loads((ROOT / 'benchmarks/tool-builds.json').read_text())
    build = next(b for b in index['builds'] if b['commit'] == integration['source_commit'])
    if build['tool_key'] != key or build['binaries'] != integration['actual_binaries']:
        raise RuntimeError('integrated compiler source catalog differs')
    lines = ['## Current integrated compiler', '',
        f"Source `{integration['source_commit'][:7]}`, tool `{key[:8]}`, passes "
        f"{integration['tests']['debug']['passed']} debug and release workspace tests (one ignored).",
        'A normal root build reproduces the exact qualified exporter, VM and wrapper.',
        'The ordinary launcher now selects this compiler. The VM is unchanged;',
        'the compiler reuses proven nonoverlapping aggregate-frame storage.',
        '[Integration qualification](results/aggregate-integration-root-01/assessment.md).', '',
        'The separate compiler comparison measures complete source-edit/build/test commands:', '',
        '| Workload | Native | Previous compiler | Integrated compiler | Paired wall | Paired CPU |',
        '| --- | ---: | ---: | ---: | ---: | ---: |']
    for case in primary['cases']:
        a = case['assessment']; m = a['median_seconds']
        lines.append(f"| {case['label']} | {m['native']:.3f}s | {m['baseline']:.3f}s | {m['candidate']:.3f}s | "
            f"{(a['wall_ratio_candidate_over_baseline']-1)*100:+.2f}% | {(a['cpu_ratio_candidate_over_baseline']-1)*100:+.2f}% |")
    lines += ['', 'Both fixed primary gates pass. The token regression remains visible.',
        'Marginal medians and paired ratios are distinct; gains from successive experiments are not added.',
        '[Primary comparison](results/aggregate-relocation-e2e-01/assessment.md).', '',
        'All seven held-outs pass their separate 5% wall/CPU guards: 588 commands,',
        '105 edited pairs and 294 artifacts. Broad qualification passes 47,004',
        'native differential commands, 245 TLS/destructor commands and 382 fre bodies',
        '(seven ignored), with fresh native controls and original assertions.',
        '[Held-outs](results/aggregate-relocation-heldout-recovery-01/assessment.md),',
        '[fre replay](results/aggregate-relocation-fre-01/assessment.md).', '',
        'The subsequent x22 budget-register experiment is parked. Its token wall gain',
        'was 1.01%, below the fixed 10% target and inside the 3.99% identical-tool',
        'variation envelope. Correctness passed; performance did not qualify it.',
        '[Fixed decision](results/budget-register-primary-01/assessment.md).', '',
        'The guarded Call-argument experiment is also parked: token wall improved',
        '1.27%, below the fixed 10% target and inside its 2.04% identical-tool envelope.',
        'It passed 297 debug/release tests and original-artifact smoke checks.',
        '[Fixed decision](results/call-slot-primary-01/assessment.md).', '',
        'The isolated whole-call candidate passes 300 debug/release tests,',
        '1,024 differential executions, strict uncalled type/borrow rejections and',
        'both original real export smokes. It expands bounded nonrecursive calls',
        'using a shared definite-initialization proof. Its completed comparison',
        'improves token wall time by 5.23% and CPU by 4.98%, beyond its 3.83% A/A',
        'envelope but below the fixed 10% target. Folded improves 0.56%, inside A/A.',
        'It is parked without integration or threshold changes.',
        '[Fixed primary decision](results/whole-call-primary-02/assessment.md).', '',
        'Token saves 291.9 ms paired execution and adds 62.7 ms Cargo time.',
        'Stage medians are descriptive and need not sum to command medians.',
        '[Recorded costs](results/whole-call-costs-01/assessment.md).', '',
        'The typed scalar observer passes 45 exporter checks and preserves both',
        'original artifacts and assertions. Five join tests and both exact profile',
        'reconciliations pass: 3,335 folded and 14,852 token boundary rows.',
        'Token has 88.54M MIR-eligible scalar argument copies and 47.67M returns.',
        'Final-bytecode admission passes eleven tests and admits 453 folded/1,542',
        'token slots. They cover 85.80M token argument copies and 47.66M returns.',
        'These counts do not predict a speedup.',
        '[Census result](results/scalar-boundary-census-01/assessment.md);',
        '[address admission](results/scalar-boundary-admission-01/assessment.md).', '',
        'The isolated versioned artifact contract passes 297 debug/release tests,',
        'one ignored, and exact legacy roundtrips. The custom interpreter now passes',
        '305 debug/release tests; serialized CLI checks pass 23 commands with',
        'native Rust controls. No scalar performance comparison has run.',
        'The custom native ABI passes 310 debug/release tests and 64 serialized',
        'CLI commands, including actual generated execution in all four JIT modes.',
        'Caller values now pass 319 debug/release tests, including all 80 scalar',
        'width/storage combinations and actual hot native transitions.',
        'Typed compiler promotion and versioned artifact publication remain next.',
        '[Caller-value qualification](results/scalar-value-calls-build-02/assessment.md);',
        'The experimental runtime is unpublished.',
        '[Native ABI](results/scalar-abi-native-build-03/assessment.md);',
        '[native CLI](results/scalar-abi-native-cli-01/assessment.md);',
        '[Interpreter](results/scalar-abi-interpreter-build-01/assessment.md);',
        '[CLI qualification](results/scalar-abi-cli-01/assessment.md);',
        '[Artifact qualification](results/scalar-abi-artifact-build-01/assessment.md);',
        '[implementation contract](benchmarks/experiments/scalar-value-abi/CONTRACT.md).', '',
        'Full libtest, unwinding, threads and general OS/FFI',
        'remain open; runtime options remain explicit.', '',
        'The following sections preserve the preceding runtime comparisons.', '']
    return lines, [dict(category='integrated-compiler-evidence', report=p,
        report_sha256=hashlib.sha256((ROOT / p).read_bytes()).hexdigest()) for p in paths]
