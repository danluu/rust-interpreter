#!/usr/bin/env python3
"""Generate current benchmark tables from the qualified aggregate and linked reports."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
CORPUS = 'results/native-controls-corpus-01/summary.json'
PREVIOUS = 'results/local-memory-forwarding-01/summary.json'
REPEATED = 'results/paired-repeated-token-01/summary.json'
COMPUTE = {'folded-literal-trie', 'token-phrase', 'forward-anchored-tls', 'pgrust-sha1-inline8'}
EXPERIMENT_RUN = 'resumable-bulk-e2e-02'
EXPERIMENT = 'results/' + EXPERIMENT_RUN + '/gate-evaluation.json'
HELD_OUT_REPORT = 'results/resumable-bulk-heldout-recovery-01/summary.json'


def verify_evidence(path, digest):
    if hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest:
        return
    bindings = json.loads((ROOT / 'results/historical-source-bindings.json').read_text())
    source = bindings['sources'].get(path)
    if path == 'scripts/verify_repeated_workflow.py' and source is not None and source['sha256'] == digest:
        content = subprocess.check_output(['git', 'show', source['commit'] + ':' + path], cwd=ROOT)
        if hashlib.sha256(content).hexdigest() == digest:
            return
    raise RuntimeError('recorded evidence changed: ' + path)


def current_mir_policy():
    path = 'results/mir-call-policy-01/summary.json'
    data = json.loads((ROOT / path).read_text())
    if data['ordinary_policy_passed'] or data['selected_policy'] != 'enlarged':
        raise RuntimeError('unexpected MIR policy decision')
    for name, digest in data['evidence'].items():
        verify_evidence(name, digest)
    lines = ['### MIR inlining policy comparison', '',
        'Ordinary inlining budgets lose to the current enlarged budgets with the',
        'same custom JIT. All 168 commands, 30 edited pairs and 84 artifacts verify.', '',
        '| Workflow | Ordinary vs enlarged wall | Ordinary vs enlarged CPU |',
        '| --- | ---: | ---: |']
    for case in data['cases']:
        row = case['assessment']
        lines.append(f"| {case['label']} | {(row['wall_ratio_ordinary_over_enlarged']-1)*100:+.2f}% | {(row['cpu_ratio_ordinary_over_enlarged']-1)*100:+.2f}% |")
    lines += ['', 'Both predeclared gates fail. Smaller artifacts and less native code did',
        'not offset the extra guest instructions and Calls. Keep enlarged inlining;',
        'no intermediate threshold sweep is planned.',
        '[Complete assessment](results/mir-call-policy-01/assessment.md).', '',
        'The [typed clearing split](results/register-clearing-attribution-01/assessment.md)',
        'assigns all 942 folded and 879 token clearing samples to guest memory;',
        'register clearing has zero sampled hits. A stronger register proof is parked.', '',
        'Historical source evidence is verified at its [recorded Git version](results/historical-source-bindings.json)',
        'when the current source has subsequently changed; original measured records remain exact.', '']
    return lines, [path, 'results/register-clearing-attribution-01/summary.json', 'results/historical-source-bindings.json']


def current_copy():
    """Render completed current receipts; never count an in-progress case."""
    original_path = 'results/resumable-copy-original-e2e-01/gate-evaluation.json'
    matched_path = 'results/resumable-copy-e2e-01/gate-evaluation.json'
    read = lambda name: json.loads((ROOT / name).read_text())
    original, matched = read(original_path), read(matched_path)
    key = '0e94d6d82b4b734e281e5b8c95a55866e5c7b0a8be53be2dafadd410708467ee'
    if original['tool_key'] != key or matched['tool_key'] != key:
        raise RuntimeError('current copy experiment tool differs')
    release = read('results/resumable-copy-release-01/summary.json')
    qualifications = [read(f'results/resumable-copy-{name}/summary.json')
                      for name in ['native-02', 'tls-01', 'fre-01']]
    if any(q['status'] != 'passed' or q['tool_key'] != key for q in qualifications):
        raise RuntimeError('current copy qualification does not match the tool')
    plan = read('benchmarks/experiments/resumable-native-calls/COPY-HELDOUTS.json')
    amendment = read('benchmarks/experiments/resumable-native-calls/COPY-HELDOUTS-RETRY-01.json')
    completed, reports = [], [original_path, matched_path,
        'results/resumable-copy-release-01/summary.json',
        *[f'results/resumable-copy-{name}/summary.json' for name in ['native-02', 'tls-01', 'fre-01']],
        'results/resumable-copy-heldout-01-case-01-stop/summary.json']
    for case in plan['cases']:
        run = case['run_id']
        if run == amendment['replacement']['original_run_id']:
            run = amendment['replacement']['retry_run_id']
        gate_path = f'results/{run}/gate-evaluation.json'
        if not (ROOT / gate_path).exists():
            continue
        gate, verified = read(gate_path), read(f'results/{run}/final-verification.json')
        if (gate['tool_key'] != key or gate['baseline_tool_key'] != original['baseline_tool_key'] or
                gate.get('held_out_case') != case['label'] or len(gate['evaluated']) != 1 or
                verified['counts'] != dict(primary_commands=63, check_commands=21, edited_pairs=15, artifacts=42)):
            raise RuntimeError('current held-out receipt identities or counts differ')
        for path, digest in verified['evidence'].items():
            verify_evidence(path, digest)
        completed.append(gate['evaluated'][0])
        reports += [gate_path, f'results/{run}/final-verification.json']
    aggregate_path = 'results/resumable-copy-heldout-recovery-01/summary.json'
    aggregate = read(aggregate_path) if (ROOT / aggregate_path).exists() else None
    if aggregate:
        if (aggregate['tool_key'] != key or aggregate['counts'] !=
                dict(primary_commands=441, check_commands=147, edited_pairs=105, artifacts=294) or
                [row['evaluation'] for row in aggregate['workflows']] != completed):
            raise RuntimeError('current complete held-out aggregate differs from its components')
        for path, digest in aggregate['evidence'].items():
            verify_evidence(path, digest)
        reports.append(aggregate_path)
    profile_lines = []
    for label in ['token', 'folded']:
        folder = f'results/resumable-copy-{label}-sample-01'
        if not (ROOT / folder / 'generated-attribution.json').exists():
            continue
        sample, attribution = read(folder + '/summary.json'), read(folder + '/generated-attribution.json')
        if (sample['tool_key'] != key or attribution['tool_key'] != key or
                sample['total_samples'] != attribution['total_thread_samples']):
            raise RuntimeError('current profile identity differs')
        classes = attribution['percentage_of_thread_samples']
        clearing = classes.get('native_zero_range', 0) + classes.get('native_zero_bulk', 0)
        profile_lines.append(f"- [{label} profile]({folder}/assessment.md): boundary self {sample['percentages'].get('native_boundary_self', 0):.2f}%; exact frame clearing {clearing:.2f}% of thread samples.")
        reports += [folder + '/summary.json', folder + '/generated-attribution.json']
    native, tls, fre = qualifications
    lines = ['## Preceding custom-copy and native-call experiment', '',
        f"Source `{original['source_commit'][:7]}`, tool `{key[:8]}` passes {release['workspace_passed']} workspace tests",
        'in debug and release, one ignored diagnostic. Copies now stay inside checked',
        'resumable native regions. The host uses LLVM; guest execution uses our own',
        'interpreter and direct AArch64 emitter.', '',
        '| Workload | Native | Original JIT baseline | Current JIT | Paired change |',
        '| --- | ---: | ---: | ---: | ---: |',
        *[f"| {r['workload']} | {r['medians']['native']:.3f} s | {r['medians']['baseline']:.3f} s | {r['medians']['candidate']:.3f} s | {(r['median_paired_ratio']-1)*100:+.2f}% |"
          for r in original['evaluated']], '',
        f"{sum(r['passed'] for r in original['evaluated'])} of {len(original['evaluated'])} original performance gates pass. These are complete source-edit/build/test",
        'commands, with fifteen pairs per workload. Both compute workloads still',
        'take longer than native Cargo. The b2 comparison includes exporter/wrapper',
        'changes; it is not an isolated measurement of the latest copy change.',
        '[Original-baseline assessment](results/resumable-copy-original-e2e-01/assessment.md).', '',
        'The separate comparison with identical exporter/wrapper binaries isolates',
        'the copy change:', '',
        *[f"- {r['workload']}: paired wall {(r['median_paired_ratio']-1)*100:+.2f}%, child CPU {(r['median_paired_cpu_ratio']-1)*100:+.2f}%; gate {'passes' if r['passed'] else 'fails'}."
          for r in matched['evaluated']], '',
        '[Matched comparison](results/resumable-copy-e2e-01/assessment.md).', '',
        f"Fresh qualification passes {native['commands']:,} mixed native-differential commands,",
        f"{tls['commands']} TLS/destructor commands, and {fre['counts']['passed']} fre test bodies ({fre['counts']['ignored']} ignored).",
        'The fre replay uses the explicit options in its report; it is not unfiltered',
        'libtest. Real unwinding, threads and general OS/FFI remain unsupported.',
        '[Fresh body replay](results/resumable-copy-fre-01/assessment.md).', '',
        *(['Fresh exact-code profiles now guide the next change:', '', *profile_lines, '',
           'These are partial, perturbed sample shares, not latency or speedup predictions.', '']
          if profile_lines else []),
        '### Current held-out verification', '',
        ('All seven histories verify together: 588 commands, 105 edited pairs and 294 artifacts.'
         if aggregate else f"{len(completed)} of seven required histories have completed partial gate verification."),
        'The original zero-pair space-guard stop remains preserved; its replacement',
        'uses an explicit amendment and the corrected admission estimate.', '',
        '| Workflow | Native | Current JIT | Paired wall vs b2 | Paired CPU vs b2 | Wall gate |',
        '| --- | ---: | ---: | ---: | ---: | --- |',
        *[f"| {r['workload']} | {r['medians']['native']:.3f} s | {r['medians']['candidate']:.3f} s | {(r['median_paired_ratio']-1)*100:+.2f}% | {(r['median_paired_cpu_ratio']-1)*100:+.2f}% | {'pass' if r['passed'] else 'fail'} |"
          for r in completed], '',
        *(['No held-out wall or CPU regression exceeds 5%.'
            if not aggregate['wall_regressions_above_5_percent'] and not aggregate['cpu_regressions_above_5_percent']
            else 'Regressions remain recorded in the complete aggregate.',
           'The narrow receipt-schema correction accepts the exact recorded job-flag',
           'metadata. Original receipts, failed attempts and gate arithmetic are preserved.',
           '[Full verification](results/resumable-copy-heldout-recovery-01/assessment.md).', '']
          if aggregate else ['A partial set cannot qualify the candidate.']),
        'Options remain explicit and disabled by default; whole-codebase compatibility',
        'and native parity on the two compute workloads remain open.',
        '[Current work](STATE.md) · [Fixed plan and retry](benchmarks/experiments/resumable-native-calls/COPY-HELDOUTS-RETRY-DECISION.md).', '',
        'The following sections preserve the preceding experiment and full-corpus baseline.', '',
    ]
    policy_lines, policy_reports = current_mir_policy()
    lines[-2:-2] = policy_lines
    reports += policy_reports
    return lines, [dict(category='current-copy-evidence', report=path,
        report_sha256=hashlib.sha256((ROOT / path).read_bytes()).hexdigest()) for path in reports]


def render():
    current_lines, current_entries = current_copy()
    from status_compiler import render as compiler_status
    compiler_lines, compiler_entries = compiler_status()
    current_lines = compiler_lines + current_lines
    current_entries = compiler_entries + current_entries
    corpus = json.loads((ROOT / CORPUS).read_text())
    previous = json.loads((ROOT / PREVIOUS).read_text())
    validation_counts = json.loads((ROOT / 'results/historical-validation-counts-01/summary.json').read_text())
    repeated = json.loads((ROOT / REPEATED).read_text())
    experiment = json.loads((ROOT / EXPERIMENT).read_text())
    experimental_checks = json.loads((ROOT / 'results' / EXPERIMENT_RUN / 'final-verification.json').read_text())['counts']
    experimental_release = json.loads((ROOT / 'results/resumable-bulk-release-01/summary.json').read_text())
    experimental_native = json.loads((ROOT / 'results/resumable-bulk-native-01/summary.json').read_text())
    experimental_tls = json.loads((ROOT / 'results/resumable-bulk-tls-01/summary.json').read_text())
    experimental_fre = json.loads((ROOT / 'results/resumable-bulk-fre-01/summary.json').read_text())
    held_out = json.loads((ROOT / HELD_OUT_REPORT).read_text())
    if (held_out['candidate_tool_key'] != experiment['tool_key'] or
            held_out['baseline_tool_key'] != experiment['baseline_tool_key'] or
            held_out['counts'] != dict(primary_commands=441, check_commands=147, edited_pairs=105, artifacts=294)):
        raise RuntimeError('held-out comparison identities or counts differ')
    for row in held_out['workflows']:
        if hashlib.sha256((ROOT / row['report']).read_bytes()).hexdigest() != row['report_sha256']:
            raise RuntimeError('held-out report changed')
    held_out_regressions = [r['workflow'] for r in held_out['workflows'] if r['median_paired_wall_ratio'] > 1.05]
    for qualification in [experimental_native, experimental_tls, experimental_fre]:
        if qualification['status'] != 'passed' or qualification['tool_key'] != experiment['tool_key']:
            raise RuntimeError('broader qualification does not match the experimental tool')
    rows = corpus['workflows']
    options = corpus['plan']['options']
    key = options['candidate_tool_key']
    builds = json.loads((ROOT / 'benchmarks/tool-builds.json').read_text())['builds']
    commit = next(b['commit'] for b in builds if b['tool_key'] == key)
    if len(rows) != len(corpus['plan']['cases']):
        raise RuntimeError('incomplete workflow corpus')
    verifications = []
    for row in rows:
        data = (ROOT / row['report']).read_bytes()
        if hashlib.sha256(data).hexdigest() != row['report_sha256']:
            raise RuntimeError('corpus input hash changed: ' + row['report'])
        verification = json.loads((ROOT / row['report']).with_name('verification.json').read_text())
        if not verification['measurement_controls_verified'] or not verification['paired_bytecode_identical']:
            raise RuntimeError('workflow controls failed: ' + row['report'])
        verifications.append(verification)
    total_commands = sum(v['commands'] + v['check_commands'] for v in verifications)
    check_commands = sum(v['check_commands'] for v in verifications)
    artifacts = sum(v['exact_artifact_hashes_verified'] for v in verifications)
    lines = [
        '# Measured status', '',
        'Generated by `python3 scripts/update_status.py` from the completed repeated',
        'native-control corpus. [Assessment](results/native-controls-corpus-01/assessment.md).', '',
        *current_lines,
        '## Previous native-call and register experiment', '',
        f"Experimental `{experiment['tool_key'][:8]}`, Git `{experiment['source_commit'][:7]}`, passes {experimental_release['workspace_passed']} workspace",
        'tests in debug and release. Three repeated source-edit cycles completed',
        f"{experimental_checks['primary_commands'] + experimental_checks['check_commands']} commands with {experimental_checks['artifacts']} identical-within-pair artifacts.",
        f"{sum(r['passed'] for r in experiment['evaluated'])} of {len(experiment['evaluated'])} original performance gates pass; the options remain disabled by default.", '',
        '| Workload | Native | Baseline JIT | Experimental JIT | Paired change |',
        '| --- | ---: | ---: | ---: | ---: |',
        *[f"| {r['workload']} | {r['medians']['native']:.3f} s | {r['medians']['baseline']:.3f} s | {r['medians']['candidate']:.3f} s | {(r['median_paired_ratio']-1)*100:+.2f}% |"
          for r in experiment['evaluated']], '',
        'Paired change is the median within-edit ratio; command columns are marginal',
        'medians. The targets remain −20% token and −10% folded against b2aa6efe.',
        'Resumable Calls and Returns now batch required initialization. Folded',
        'passes; token narrowly misses its target (ratio 0.8003441753 versus 0.8).',
        'Both fixed-tool runs fail the token gate. The first improved folded 19.51%',
        'and token 19.95%; this replication improved 19.15% and 19.97%. All pairs',
        'and both decisions are preserved. Broader native differential and TLS',
        'checks and fresh fre body replay now pass, along with the held-out checks below.',
        'Defaults and original criteria remain unchanged.',
        '[Both runs and per-edit variation](results/resumable-bulk-replication-01/assessment.md).',
        f'[Result and limitations](results/{EXPERIMENT_RUN}/assessment.md).', '',
        '## Previous held-out comparison', '',
        'Six completed original cases plus one fresh Nushell retry verify 588 commands,',
        '105 edited pairs and 294 artifacts. The original disk-full run remains',
        'incomplete; its partial records are preserved outside these totals.', '',
        '| Workflow | Paired wall change | Paired CPU change |',
        '| --- | ---: | ---: |',
        *[f"| {r['workflow']} | {(r['median_paired_wall_ratio']-1)*100:+.2f}% | {(r['median_paired_cpu_ratio']-1)*100:+.2f}% |"
          for r in held_out['workflows']], '',
        ('No case exceeds the predeclared 5% paired wall regression limit.' if not held_out_regressions else
         'Cases above the 5% paired wall regression limit: ' + ', '.join(held_out_regressions) + '.'),
        'This engineering limit is not a confidence interval. Both original token gates',
        'remain failed. Native-call options remain experimental and disabled by default.',
        '[Two histories and verification](results/resumable-bulk-heldout-recovery-01/assessment.md).', '',
        '## Full-corpus baseline', '',
        f"Full-corpus engine `{key[:8]}`, Git `{commit[:7]}`; paired baseline `{options['baseline_tool_key'][:8]}`.",
        'The current change fixes codegen-limit handling; these measurements do not',
        'establish a runtime improvement over that baseline. Native uses explicit',
        f"root O0/incremental settings, {options['native_jobs']} Cargo jobs and default test concurrency.",
        'Manifest package overrides remain in effect.',
        f"Custom builds use {options['jobs']} Cargo jobs and the per-workflow MIR/runtime settings in",
        '[the pinned corpus](benchmarks/workflow-corpus.json). Linker/backend tuning',
        'is still unqualified; this is not a fastest-native claim.', '',
        f"All numbers below are median complete commands after five different edits",
        f"repeated through {options['cycles']} cycles on one shared Apple Silicon macOS host.",
        'They include launcher, compilation/export, linking where applicable,',
        'and selected test execution. Ratio is custom/native; lower is faster.', '',
    ]
    for heading, is_compute in [('Workflows with material guest execution', True), ('Workflows dominated by frontend/linking', False)]:
        lines += ['## ' + heading, '', '| Workflow | Native | Custom JIT | Ratio | Check reference |', '| --- | ---: | ---: | ---: | ---: |']
        for row in rows:
            if (row['label'] in COMPUTE) != is_compute:
                continue
            n, c = row['medians']['native'], row['medians']['candidate']
            lines.append(f"| [{row['label']}]({row['report']}) | {n:.3f} s | {c:.3f} s | {c/n:.2f}× | {row['check_median_seconds']:.3f} s |")
        lines += ['']
    lines += [
        'The independent check command uses the native profile/flags/jobs and a',
        'separate cache. It checks the library test target without executing tests.',
        'Its wall time is a reference, not an additive component or causal floor.', '',
        '## Verification and variation', '',
        f"All {total_commands} commands completed, including {check_commands} independent checks.",
        f"Wrong production edits were rejected; {artifacts} artifacts were hash-verified and",
        'corresponding JIT versions received identical bytecode. Original assertions',
        'and test sources were preserved. Child CPU, per-edit spreads, cold commands',
        'and source-reverting cycle anchors are retained in each linked report.', '',
        'Identical source after the first edit cycle can produce a different artifact',
        'layout. This occurred in all three fre workflows here. Cross-history semantic',
        'equivalence and the cause of the layout differences remain unresolved.',
        'All samples, including the slow token sample, remain in the reports.', '',
        '## Earlier repeated token comparison', '',
        f"Three cycles, fifteen edited pairs: native {repeated['median_seconds']['native']:.3f} s,",
        f"previous JIT {repeated['median_seconds']['baseline']:.3f} s, retained JIT {repeated['median_seconds']['candidate']:.3f} s.",
        'Corresponding engines used identical bytecode, but revisiting the same',
        'source after the first cycle changed artifact layout. The failed stronger',
        'identity check is preserved. [Assessment](results/paired-repeated-token-01/assessment.md).', '',
        '## Coverage and limits', '',
        'That full-corpus source passed 188 bytecode unit/integration, 11 exporter and',
        '3 historical-cache tests. [Test receipt](results/review-codegen-limits-01/summary.json).',
        f"The earlier `{previous['retained_tool_key'][:8]}` qualification completed {validation_counts['commands']:,} mixed commands:",
        f"{validation_counts['counts']['vm-jit']:,} JIT and {validation_counts['counts']['vm-interpreter']:,} interpreter invocations, plus native builds/runs,",
        'exports and rejection checks across two inlining modes. These are command',
        'counts, not unique test cases. [Recount](results/historical-validation-counts-01/assessment.md).',
        'A separate 245-command TLS qualification also passed.',
        f"Experimental `{experiment['tool_key'][:8]}` now independently passes {experimental_native['commands']:,} mixed commands",
        'with its exact runtime options: 22,238 JIT and 22,238 interpreter',
        'invocations across two modes, plus native controls/exports/rejections.',
        'Both modes executed resumable Calls/Returns; successful JIT runs had',
        'no declined functions. [Validation](results/resumable-bulk-native-01/assessment.md).',
        f"Its separate {experimental_tls['commands']}-command [TLS/destructor suite](results/resumable-bulk-tls-01/assessment.md) also passes.",
        f"Fresh experimental fre coverage recollected {experimental_fre['selected']} original bodies:",
        f"{experimental_fre['counts']['passed']} passed and {experimental_fre['counts']['ignored']} were ignored, with {experimental_fre['fresh_native_controls']} fresh native executions.",
        f"Of {experimental_fre['compared_artifacts']} compared artifact hashes, {experimental_fre['changed_artifacts']} changed; {len(experimental_fre['outcome_changes'])} outcomes changed.",
        f"Maximum generated code was {experimental_fre['maximum_generated_bytes']:,} bytes, with {experimental_fre['executions_with_declines']} successful executions declining functions.",
        '[Fresh body qualification](results/resumable-bulk-fre-01/assessment.md).', '',
        'Both fre replays required `--allocation-limit 150000 --trap-unsupported-calls` and',
        '`--run-try-callbacks`, plus the recorded MIR/inlining settings. They invoke',
        'test bodies directly; it is not unfiltered libtest or whole-application',
        'coverage. Lowered audit entries are not counted as executed tests.', '',
        'No whole-codebase development workflow is qualified yet. Real unwinding,',
        'general OS/FFI use, threads and complete libtest semantics remain missing.',
        'Toolchain, fetched dependencies and std-MIR setup precede the reported',
        'cold Cargo commands. OS caches were not cleared.', '',
        '[All current evidence](results/INDEX.md) · [Protocol](BENCHMARKING.md) ·',
        '[Next work](RUNTIME-NEXT.md) · [Review decisions](docs/SUGGESTIONS-REVIEW-20260910.md)', '',
    ]
    entries = current_entries + [dict(category='workflow', workflow=r['label'], report=r['report'],
        report_sha256=r['report_sha256'], measured_tool_key=key,
        native_seconds=r['medians']['native'], custom_seconds=r['medians']['candidate']) for r in rows]
    for category, report in [
        ('held-out-recovery-comparison', HELD_OUT_REPORT),
        ('preserved-incomplete-workflow', 'results/resumable-bulk-heldout-failure-01/summary.json'),
        ('interface-qualification', 'results/interface-pgrust-qualification-01/summary.json'),
        ('workflow-io-qualification', 'results/workflow-io-faults-02/summary.json'),
        ('held-out-verifier-qualification', 'results/resumable-heldout-verifier-01/summary.json'),
        ('experimental-fre-validation', 'results/resumable-bulk-fre-01/summary.json'),
        ('experimental-native-validation', 'results/resumable-bulk-native-01/summary.json'),
        ('experimental-tls-validation', 'results/resumable-bulk-tls-01/summary.json'),
        ('body-driver-qualification', 'results/resumable-body-drivers-02/summary.json'),
        ('historical-count-correction', 'results/historical-validation-counts-01/summary.json'),
        ('runtime-replication', 'results/resumable-bulk-replication-01/summary.json'),
        ('first-bulk-run', 'results/resumable-bulk-e2e-01/summary.json'),
        ('coverage-driver-qualification', 'results/resumable-coverage-drivers-01/summary.json'),
        ('runtime-experiment', 'results/' + EXPERIMENT_RUN + '/summary.json'),
        ('runtime-gates', EXPERIMENT),
        ('runtime-verification', 'results/' + EXPERIMENT_RUN + '/final-verification.json'),
        ('release-qualification', 'results/resumable-bulk-release-01/summary.json'),
        ('execution-smoke', 'results/resumable-bulk-real-smoke-01/summary.json'),
        ('cli-qualification', 'results/resumable-bulk-cli-01/summary.json'),
        ('previous-runtime-experiment', 'results/resumable-e2e-01/summary.json'),
        ('execution-driver-qualification', 'results/resumable-execution-driver-01/summary.json'),
        ('previous-runtime-experiment', 'results/persistent-e2e-01/summary.json'),
        ('previous-runtime-experiment', 'results/native-region-e2e-01/summary.json'),
        ('generated-code-attribution', 'results/resumable-folded-sample-01/generated-attribution.json'),
        ('generated-code-attribution', 'results/resumable-token-sample-01/generated-attribution.json'),
        ('diagnostic-tool-qualification', 'results/resumable-profile-tools-01/summary.json'),
        ('generated-code-attribution', 'results/persistent-folded-sample-01/generated-attribution.json'),
        ('generated-code-attribution', 'results/persistent-token-sample-01/generated-attribution.json'),
        ('diagnostic-tool-qualification', 'results/persistent-profile-tools-02/summary.json'),
        ('parked-frame-reuse-scope', 'results/aggregate-reuse-weights-01/summary.json'),
        ('resumable-storage-qualification', 'results/resumable-frames-01/summary.json'),
        ('resumable-boundary-qualification', 'results/resumable-boundary-01/summary.json'),
        ('resumable-release-qualification', 'results/resumable-boundary-release-01/summary.json'),
        ('observer-qualification', 'results/aggregate-reuse-build-01/summary.json'),
        ('observer-artifact-qualification', 'results/aggregate-reuse-collection-01/summary.json'),
        ('diagnostic-release', 'results/native-code-dump-release-01/summary.json'),
        ('diagnostic', 'results/native-region-token-sample-01/summary.json'),
        ('diagnostic', 'results/native-region-folded-sample-01/summary.json'),
        ('generated-code-attribution', 'results/native-code-token-sample-02/generated-attribution.json'),
        ('generated-code-attribution', 'results/native-code-folded-sample-01/generated-attribution.json'),
        ('preserved-incomplete-capture', 'results/native-code-token-sample-01/capture-status.json'),
        ('corpus', CORPUS), ('previous-corpus', PREVIOUS), ('repeated-workflow', REPEATED),
        ('source-qualification', 'results/review-codegen-limits-01/summary.json'),
        ('diagnostic', 'results/retained-token-cpu-sample-04/summary.json'),
        ('diagnostic', 'results/frame-initialization-census-01/summary.json'),
        ('diagnostic', 'results/mir-frame-census-01/summary.json'),
        ('diagnostic', 'results/native-call-census-01/summary.json'),
        ('diagnostic', 'results/native-call-census-02/summary.json'),
        ('control-qualification', 'results/paired-native-controls-pgrust-02/summary.json'),
        ('control-qualification', 'results/e2e-native-controls-reference-01/summary.json'),
    ]:
        entries.append(dict(category=category, report=report,
            report_sha256=hashlib.sha256((ROOT / report).read_bytes()).hexdigest()))
    index = ['# Current evidence index', '',
        'Generated by `python3 scripts/update_status.py`; hashes are in [index.json](index.json).',
        'This selects the current evidence. Historical reports remain at their original',
        'paths; omission is not deletion, supersession, or proof of irrelevance.', '',
        '| Category | Report |', '| --- | --- |']
    for entry in entries:
        path = entry['report'].removeprefix('results/')
        index.append(f"| {entry['category']} | [{entry.get('workflow', path)}]({path}) |")
    index += ['', '[Measured status](../STATUS.md) · [Earlier native-cache results](../RESULTS.md)', '']
    return {'STATUS.md': '\n'.join(lines), 'results/INDEX.md': '\n'.join(index),
        'results/index.json': json.dumps(dict(schema_version=1, entries=entries), indent=2) + '\n'}


if __name__ == '__main__':
    from status_current import render as current_status
    outputs = render()
    outputs['STATUS.md'] = current_status()
    for name, content in outputs.items():
        (ROOT / name).write_text(content)
