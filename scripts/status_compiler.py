"""Current integrated compiler evidence for the generated status page."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def render():
    paths = [f'results/{run}/summary.json' for run in (
        'aggregate-integration-root-01', 'aggregate-relocation-e2e-01',
        'aggregate-relocation-heldout-recovery-01', 'budget-register-primary-01')]
    integration, primary, held, budget = [json.loads((ROOT / p).read_text()) for p in paths]
    key = integration['tool_key']
    if not (all(d['status'] == 'passed' for d in (integration, primary, budget))
            and held['status'] == 'all seven histories verified'
            and integration['component_identity_matches']
            and integration['actual_binaries'] == integration['expected_binaries']
            and primary['expected_tools']['candidate']['tool_key'] == key
            and primary['primary_performance_gates_passed']
            and held['heldout_gates_passed']
            and not budget['primary_gates_passed']):
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
        'Next: use existing profiles to measure static argument/result slot opportunities',
        'in native Calls and Returns. Full libtest, unwinding, threads and general OS/FFI',
        'remain open; runtime options remain explicit.', '',
        'The following sections preserve the preceding runtime comparisons.', '']
    return lines, [dict(category='integrated-compiler-evidence', report=p,
        report_sha256=hashlib.sha256((ROOT / p).read_bytes()).hexdigest()) for p in paths]
