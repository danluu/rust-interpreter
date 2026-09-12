"""Concise current status from one manifest; historical detail stays in results."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(name):
    return json.loads((ROOT / name).read_text())


def render():
    config = read('benchmarks/current-status.json')
    integration = read(config['integration'])
    primary, held = read(config['primary']), read(config['heldout'])
    if (integration['tool_key'] != config['tool_key'] or
            not integration['component_identity_matches'] or
            not primary['primary_performance_gates_passed'] or not held['heldout_gates_passed']):
        raise RuntimeError('current retained evidence differs from manifest')
    cases = [(c['label'], c['run_id']) for c in primary['cases'] + held['cases']]
    lines = ['# Current measured status', '',
        f"Retained build **{config['source_commit'][:7]}/{config['tool_key'][:8]}**: custom interpreter and direct AArch64 JIT, strict rustc type/borrow checking. The exec Cargo wrapper is deployed.", '',
        'The retained measurements put folded near the specified native control and token about 2.3× slower. Other selected workflows save code-generation/link time while executing their original assertions. Native uses project debuginfo/link settings; fre debuginfo calibration selected no replacement preset. Large native controls and full libtest compatibility remain open.', '',
        'Times below come from each row’s own three-cycle, five-edit history. Native uses O0/incremental, 18 jobs/default test threads; custom uses four jobs. Cold means empty per-mode caches, excluding tool/sysroot bootstrap and OS cache coldness.', '',
        '| Workflow | Warm native | Warm custom | Cargo check | Custom/check | Cold native | Cold custom |',
        '| --- | ---: | ---: | ---: | ---: | ---: | ---: |']
    cold_losses = 0
    for label, run in cases:
        report = read(f'results/{run}/summary.json')
        if report['tool_builds']['candidate']['tool_key'] != config['tool_key']:
            raise RuntimeError('status row uses a different tool')
        warm, cold = report['median_seconds'], report['cold_success_seconds']
        check = report['check_floor']['median_seconds']
        cold_losses += cold['candidate'] > cold['native']
        lines.append(f"| [{label}](results/{run}/summary.json) | {warm['native']:.3f}s | {warm['candidate']:.3f}s | {check:.3f}s | {warm['candidate']/check:.2f}× | {cold['native']:.3f}s | {cold['candidate']:.3f}s |")
    lines += ['',
        f'Custom cold commands are slower on {cold_losses} of {len(cases)} rows. Cargo check executes no tests; custom/check is a descriptive overhead comparison, not a causal subtraction. Paired changes establish version comparisons; cross-session absolute medians do not.', '',
        'Retained qualification: 289 debug/release tests (one ignored), 47,004 broad validation commands, 245 TLS/destructor commands and 382 fre body passes (seven ignored). Seven held-out histories passed separate 5% wall/CPU regression guards. Private results expose aggregates only.', '',
        'The lightweight wrapper is in the retained build despite failing its standalone cold-performance gate. Budget-register, call-slot and whole-call candidates remain parked. A new 18-custom-worker latency preset is on the development branch; it does not alter the measurements above.', '']
    screen, decision = read(config['latest_screen']), read(config['latest_decision'])
    costs = read(config['latest_export_costs'])
    coverage = read(config['latest_integration_coverage'])
    edit = read(config['latest_integration_edit'])
    compute = read(config['latest_integration_compute'])
    if coverage['status'] != 'passed' or edit['status'] != 'passed' or compute['status'] != 'passed':
        raise RuntimeError('integration target evidence changed')
    if costs['status'] != 'passed' or not costs['all_artifact_hashes_identical']:
        raise RuntimeError('export cost evidence changed')
    emit = costs['stage_medians']['emit']
    if screen['status'] != 'passed' or decision['status'] != 'parked' or screen['advance_to_full_comparison']:
        raise RuntimeError('latest scalar decision changed')
    lines += ['**Latest scalar ABI screen: parked.** Five real edits per case, original tests and wrong-edit controls; all correctness checks passed.', '',
        '| Workload | Paired wall change | Paired CPU change |', '| --- | ---: | ---: |']
    for case in screen['cases']:
        lines.append(f"| {case['label']} | {(case['wall_ratio']-1)*100:+.2f}% | {(case['cpu_ratio']-1)*100:+.2f}% |")
    lines += ['',
        'Token missed the 8% screening target. Execution saved about 170ms paired while Cargo added 144ms. Full scalar A/A and held-outs are stopped. Source lives under `crates/` on `experiment/scalar-value-abi` (measured commit `840fdb5`); the timing tool used the same wrapper on both sides.', '',
        '[Scalar assessment](results/scalar-edit-smoke-01/assessment.md).', '',
        f"**Latest exporter attribution:** seven real token artifacts match the retained compiler exactly. Graph lowering costs {emit['lower_graph']*1000:.0f}ms; hashing {emit['call_report_hash']*1000:.0f}ms, publication {emit['bytecode_publication']*1000:.0f}ms, serialization {emit['serialization']*1000:.0f}ms and validation {emit['validation']*1000:.0f}ms. [Assessment]({Path(config['latest_export_costs']).with_name('assessment.md')}).", '',
        f"Effective profiles are recorded for all five projects: pgrust/Ruff already use line tables; all use unpacked split debuginfo. [Native stage attribution]({Path(config['latest_native_stages']).with_name('assessment.md')}) covers 135 existing edited commands.", '',
        f"[Fre native calibration]({Path(config['latest_native_calibration']).with_name('assessment.md')}) was inconclusive: line tables saved 7.86%, below its fixed 8% screen; debug=0 saved 5.17%. All 21 Cargo commands and 15 diagnostic repeats had the expected assertion outcomes. No new native preset was selected.", '',
        f"The [unfiltered fre command]({Path(config['latest_unfiltered']).with_name('assessment.md')}) passed 382 unit and 52 integration tests (seven ignored), then failed a doc test whose expected diagnostic code was absent. The root launcher now runs all {coverage['original_tests_passed']} original integration assertions across {coverage['targets_passed']} targets with shared dependency metadata. [Coverage]({Path(config['latest_integration_coverage']).with_name('assessment.md')}).", '',
        f"The [integration edit pilot]({Path(config['latest_integration_edit']).with_name('assessment.md')}) records five real edits: custom {edit['median_seconds']['custom']:.3f}s, native {edit['median_seconds']['native']:.3f}s, Cargo check {edit['median_seconds']['check']:.3f}s; paired wall {(edit['paired_median_wall_ratio']-1)*100:+.1f}%. Both sides use 18 jobs. This one-cycle pilot is separate from the retained histories above.", '',
        f"The [compute-heavy integration target]({Path(config['latest_integration_compute']).with_name('assessment.md')}) costs {compute['median_seconds']['custom']:.3f}s custom versus {compute['median_seconds']['native']:.3f}s native ({compute['paired_median_wall_ratio']:.3f}× paired), with check at {compute['median_seconds']['check']:.3f}s. All 24 edit/restoration controls pass. Native uses default test threads; custom runs its two bodies sequentially. Generated execution dominates the [profile]({Path(config['latest_integration_profile']).with_name('assessment.md')}).", '',
        f"[Source restoration now refreshes modification time]({Path(config['latest_source_restore']).with_name('assessment.md')}) so Cargo rebuilds the restored original. Actual Cargo regressions and 18 Python tests pass. Remaining original-source bytecode differences keep export determinism open.", '',
        '**Open adoption work:** tuned native controls; complete test-suite execution; unwinding, threads and general OS/FFI; deterministic/reusable export graphs. Selected test-body results are not whole-project qualification.', '',
        '**Next:** ' + config['next'], '',
        f"[Review decisions]({config['review']}) · [Work state](STATE.md) · [Evidence index](results/INDEX.md) · [Retention policy](results/RETENTION.md)", '',
        'Generated by `python3 scripts/update_status.py` from `benchmarks/current-status.json` and the linked receipts.', '']
    return '\n'.join(lines)
