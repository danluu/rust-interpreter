#!/usr/bin/env python3
"""Report both predeclared runs without changing their independent gate decisions."""
from collections import Counter
import hashlib
import json
from pathlib import Path
from statistics import median
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from verify_repeated_workflow import require

RUNS = ['resumable-bulk-e2e-01', 'resumable-bulk-e2e-02']
TARGETS = {'folded-literal-trie': .9, 'token-phrase': .8}
CONTROLS = ['project', 'workflow', 'revision', 'cycles', 'tests', 'edits', 'case_sha256',
            'batch', 'cargo_timings', 'vary_selection', 'build_tool_opt_level', 'build_jobs',
            'native_control', 'instruction_limit', 'allocation_limit', 'tool_builds', 'scripts_sha256']


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path, evidence):
    evidence[str(path.relative_to(ROOT))] = sha(path)
    return json.loads(path.read_text())


def spread(values):
    return dict(min=min(values), median=median(values), max=max(values))


def main():
    evidence, runs, counts = {}, {}, Counter()
    for name in RUNS:
        directory = ROOT / 'results' / name
        gate = read(directory / 'gate-evaluation.json', evidence)
        final = read(directory / 'final-verification.json', evidence)
        corpus = read(directory / 'summary.json', evidence)
        receipt = read(ROOT / '.work/experiments' / name / 'status.json', evidence)
        require(receipt['status'] == 'finished' and receipt['returncode'] == 0, 'run is not terminal0')
        require(final['counts'] == dict(primary_commands=126, check_commands=42, edited_pairs=30, artifacts=84),
                'unexpected completed run counts')
        require(final['frozen_scripts_unchanged'] and final['candidate_option_verified'], 'unverified controls')
        for path, digest in final['evidence'].items():
            require(sha(ROOT / path) == digest, 'previously verified workflow evidence changed')
        counts.update(final['counts'])
        reports = {}
        for row in corpus['workflows']:
            path = ROOT / row['report']
            report = read(path, evidence)
            require(evidence[row['report']] == row['report_sha256'], 'corpus/workflow mismatch')
            check = read(path.with_name('verification.json'), evidence)
            require(check['paired_bytecode_identical'] and check['measurement_controls_verified'], 'unverified pairs')
            pairs = report['comparison']['pairs']
            require({(p['cycle'], p['state']) for p in pairs} == {(c, s) for c in range(3) for s in range(1, 6)}
                    and len(pairs) == 15 and all(p['identical_bytecode'] for p in pairs), 'incomplete edit matrix')
            result = next(r for r in gate['evaluated'] if r['workload'] == row['label'])
            ratio = median(p['candidate_seconds'] / p['baseline_seconds'] for p in pairs)
            cpu = median(p['candidate_cpu_seconds'] / p['baseline_cpu_seconds'] for p in pairs)
            require(result['median_paired_ratio'] == ratio and result['median_paired_cpu_ratio'] == cpu
                    and result['target_max_ratio'] == TARGETS[row['label']]
                    and result['passed'] == (ratio <= TARGETS[row['label']] and cpu < 1), 'gate changed')
            reports[row['label']] = dict(report=report, verification=check, gate=result)
        require(set(reports) == set(TARGETS), 'unexpected workflows')
        runs[name] = dict(gate=gate, final=final, reports=reports, options=corpus['plan']['options'])

    first, second = [runs[r] for r in RUNS]
    for field in ['source_commit', 'tool_key', 'baseline_tool_key']:
        require(first['gate'][field] == second['gate'][field], 'replicated tool/source changed')
    for field in ['installed_binaries_verified', 'source_pins']:
        require(first['final'][field] == second['final'][field], 'replicated binaries/pins changed')
    require({k: v for k, v in first['options'].items() if k != 'run_id'} ==
            {k: v for k, v in second['options'].items() if k != 'run_id'}, 'replication options changed')
    workflows = {}
    lines = ['# Fixed-tool replication', '',
             'Both original runs remain in the record. Each gate uses its own fifteen',
             'edited pairs; no pooled retention criterion or repeated attempt is used.', '',
             '| Workload | Run | Paired wall change | Paired CPU change | Original gate |',
             '| --- | --- | ---: | ---: | --- |']
    for label in TARGETS:
        a, b = [r['reports'][label] for r in [first, second]]
        for field in CONTROLS:
            require(a['report'][field] == b['report'][field], 'replicated workflow control changed: ' + field)
        require(a['report']['std_mir']['key'] == b['report']['std_mir']['key'], 'std MIR changed')
        pairs, per_run = [], []
        signatures = []
        for name, data in zip(RUNS, [a, b]):
            report, gate = data['report'], data['gate']
            per_run.append(dict(run_id=name, gate=gate, cross_cycle_bytecode_identical=data['verification']['cross_cycle_bytecode_identical']))
            for pair in report['comparison']['pairs']:
                pairs.append(dict(run_id=name, wall_ratio=pair['candidate_seconds'] / pair['baseline_seconds'],
                    cpu_ratio=pair['candidate_cpu_seconds'] / pair['baseline_cpu_seconds'], **pair))
            signatures.append({(s['cycle'], s['state'], s['mode']):
                (s['source_sha256'], [(x['sha256'], x['bytes']) for x in s['artifacts']])
                for s in report['samples']})
            lines.append(f"| {label} | {name} | {(gate['median_paired_ratio']-1)*100:+.2f}% | "
                         f"{(gate['median_paired_cpu_ratio']-1)*100:+.2f}% | {'pass' if gate['passed'] else 'fail'} |")
        require(signatures[0].keys() == signatures[1].keys(), 'replicated state matrix differs')
        per_edit = []
        for state, edit in enumerate(a['report']['edits'], 1):
            selected = [p for p in pairs if p['state'] == state]
            require(len(selected) == 6 and len({p['source_sha256'] for p in selected}) == 1, 'replicated edit source differs')
            per_edit.append(dict(state=state, edit=edit, runs={name: {field: spread([p[field] for p in selected if p['run_id'] == name])
                for field in ['wall_ratio', 'cpu_ratio', 'native_seconds', 'baseline_seconds', 'candidate_seconds',
                              'native_cpu_seconds', 'baseline_cpu_seconds', 'candidate_cpu_seconds']}
                for name in RUNS}))
        workflows[label] = dict(runs=per_run, pairs=pairs, per_edit=per_edit,
            same_gate_classification=a['gate']['passed'] == b['gate']['passed'],
            cross_run_matching_history_artifacts_identical=signatures[0] == signatures[1])
    lines += ['', f"All {counts['primary_commands']+counts['check_commands']} commands, including {counts['check_commands']} independent Cargo checks, are preserved.",
              f"There are {counts['edited_pairs']} edited pairs across both workloads and {counts['artifacts']} verified artifacts.",
              'Corresponding engines receive identical bytecode. Cross-cycle bytecode',
              'layout differences remain unresolved; matching corresponding histories',
              'across these two runs would not prove general determinism.', '',
              'Per-edit wall/CPU variation is descriptive. These six samples per edit',
              'share cache-history and host conditions; no independent-sample confidence',
              'interval, unique-case count or significance claim is inferred.', '']
    for label, data in workflows.items():
        lines += ['## ' + label, '',
                  'The original gate classification ' + ('agrees between runs.' if data['same_gate_classification'] else 'differs between runs and is unstable at this threshold.'), '',
                  '| Edit | Run | Wall ratio median [min, max] | CPU ratio median [min, max] |',
                  '| --- | --- | ---: | ---: |']
        for edit in data['per_edit']:
            for name, values in edit['runs'].items():
                wall, cpu = values['wall_ratio'], values['cpu_ratio']
                lines.append(f"| {edit['edit']} | {name[-2:]} | {wall['median']:.4f} [{wall['min']:.4f}, {wall['max']:.4f}] | "
                             f"{cpu['median']:.4f} [{cpu['min']:.4f}, {cpu['max']:.4f}] |")
        lines += ['']
    lines += ['The measured mode remains experimental. Broader execution qualification and',
              'seven held-out workflows are still required before retention. Native',
              'profile/jobs, setup exclusions and whole-application limitations remain',
              'those of the original protocol. No unrelated workload was controlled.', '',
              '[All pairs and evidence hashes](summary.json) ·',
              '[Protocol](../../benchmarks/experiments/resumable-native-calls/REPLICATION.md)', '']
    evidence[str(Path(__file__).relative_to(ROOT))] = sha(Path(__file__))
    protocol = Path(__file__).with_name('REPLICATION.md')
    evidence[str(protocol.relative_to(ROOT))] = sha(protocol)
    require(all(sha(ROOT / p) == h for p, h in evidence.items()), 'input changed during report')
    out = ROOT / 'results/resumable-bulk-replication-01'
    out.mkdir(exist_ok=False)
    (out / 'summary.json').write_text(json.dumps(dict(tool_key=first['gate']['tool_key'],
        source_commit=first['gate']['source_commit'], counts=dict(counts), workflows=workflows,
        evidence=evidence, retained=False, pooled_retention_rule=False), indent=2) + '\n')
    (out / 'assessment.md').write_text('\n'.join(lines))
    print(json.dumps({k: dict(gates=[r['gate']['passed'] for r in v['runs']],
        cross_run_matching_history_artifacts_identical=v['cross_run_matching_history_artifacts_identical'])
        for k, v in workflows.items()}))


if __name__ == '__main__':
    main()
