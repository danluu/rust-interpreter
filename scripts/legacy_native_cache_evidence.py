"""Ownership of a bounded catalog of completed pre-interpreter Cargo caches.

Legacy commands have per-build completion records instead of a supervisor.
Their original result format and all failures remain intact. No old compiler
backend is invoked here, and no guest-execution fallback is introduced.
"""
import json
from pathlib import Path
import subprocess

from verify_repeated_workflow import require

CATALOG = 'benchmarks/legacy-native-cache-catalog.json'
GROUPS = {(run, project): repeats
          for run, repeats, projects in [
              ('dev-profiles-03', 5, ['nushell', 'ruff', 'pgrust']),
              ('pilot-02', 3, ['nushell', 'ruff', 'pgrust']),
              ('native-repository-04', 3, ['pgrust'])]
          for project in projects}


def select(catalog, root, identity, corpus, mode):
    require(catalog['schema_version'] == 1 and catalog['owner'] == str(root),
            'legacy catalog owner or schema differs')
    require(mode == 'native', 'legacy Cargo targets require native cache mode')
    groups = catalog['groups']
    require(len(groups) == len(GROUPS) and
            {(g['run'], g['project']) for g in groups} == set(GROUPS),
            'legacy catalog scope differs')
    selected = []
    for group in groups:
        run, project = group['run'], group['project']
        variants = ['llvm', 'llvm-unwind'] if run == 'native-repository-04' else ['llvm', 'clif', 'clif-cache']
        require(group['repeats'] == GROUPS[run, project] and group['variants'] == variants,
                'legacy repetitions or variants differ')
        for variant in variants:
            if identity == run + '-' + project + '-' + variant:
                require(corpus == run, 'legacy corpus identity differs')
                selected.append((group, variant))
    require(len(selected) == 1, 'legacy target is not in the explicit public catalog')
    return selected[0]


def validate_records(root, group, provenance, rows, summary):
    run, project = group['run'], group['project']
    variants = group['variants']
    require(provenance['variants'] == variants and summary['run'] == run,
            'legacy variant selection or summary identity differs')
    require('commit-hash: cea272fa356e94bd2ee2cadf376630aa0683867a' in provenance['compiler'],
            'legacy compiler revision differs')
    cases = [('cold', 'A'), ('no-op', 'A')]
    for i in range(group['repeats']):
        cases.extend([('body-edit', 'B' if run == 'pilot-02' else 'B%04d' % i), ('revert', 'A'), ('no-op', 'A')])
    expected = [(variant, case, state) for i, (case, state) in enumerate(cases)
                for variant in (variants if i % 2 == 0 else variants[::-1])]
    require([(row['variant'], row['case'], row['state']) for row in rows] == expected and
            [row['ordinal'] for row in rows] == list(range(len(expected))),
            'legacy complete command schedule differs')
    state_sources = {}
    for row in rows:
        require(row['project'] == project and row['status'] == 'ok' and row['exit_code'] == 0 and
                type(row['pid']) is int and row['pid'] > 0,
                'legacy build/runtime validation was not successfully terminal')
        target = root / '.work/targets' / run / project / row['variant']
        binary = Path(row['binary'])
        require(row['target_dir'] == str(target) and binary.is_absolute() and binary.resolve() == binary and
                binary != target and binary.is_relative_to(target),
                'legacy target or executable escaped the recorded cache')
        command = row['command']
        require(command[:3] == ['cargo', '+nightly-2026-09-08', 'build'] and
                '--locked' in command and '--offline' in command and
                command[command.index('--jobs') + 1] == str(provenance['jobs']) and
                command[command.index('--target') + 1] == 'aarch64-apple-darwin',
                'legacy Cargo invocation differs')
        require(row['build_seconds'] > 0 and row['runtime_seconds'] > 0 and
                len(row['runtime_stdout_sha256']) == 64, 'legacy runtime completion evidence missing')
        state_sources.setdefault(row['state'], set()).add(row['source_sha256'])
    require(all(len(values) == 1 for values in state_sources.values()) and
            len({next(iter(values)) for values in state_sources.values()}) ==
            (2 if run == 'pilot-02' else 1 + group['repeats']),
            'legacy source states are inconsistent or unchanged')
    selected = [entry for entry in summary['summary'] if entry['project'] == project]
    require(len(selected) == len(variants) * 4 and
            {(e['variant'], e['case']) for e in selected} ==
            {(v, c) for v in variants for c in ['cold', 'no-op', 'body-edit', 'revert']},
            'legacy project summary is incomplete')
    for entry in selected:
        count = sum(row['variant'] == entry['variant'] and row['case'] == entry['case'] for row in rows)
        require(entry['n'] == count, 'legacy report command counts differ')


def cache(root, identity, corpus, mode, sha):
    read = lambda path: json.loads(path.read_text())
    catalog_path = root / CATALOG
    catalog = read(catalog_path)
    group, variant = select(catalog, root, identity, corpus, mode)
    run, project = group['run'], group['project']
    raw = root / '.work/runs' / run / project
    source_record = root / '.work/runs' / run / 'source-record'
    report_path = root / 'results' / run / 'summary.json'
    proofs = {CATALOG: sha(catalog_path)}
    require(raw.resolve(strict=True) == raw and source_record.resolve(strict=True) == source_record,
            'legacy evidence root is noncanonical')
    require({str(p.relative_to(root)) for p in raw.iterdir() if p.is_file()} ==
            {name for name in group['evidence'] if Path(name).parent == raw.relative_to(root)},
            'legacy direct evidence file set changed')
    for name, expected in group['evidence'].items():
        path = root / name
        require(not Path(name).is_absolute() and '..' not in Path(name).parts and
                path.resolve(strict=True) == path and path.is_file() and
                (path.parent == raw or path.is_relative_to(source_record) or path == report_path) and
                sha(path) == expected, 'legacy catalog evidence changed or escaped its scope')
        proofs[name] = expected
    required = [raw / 'provenance.json', raw / 'results.jsonl', report_path, root / group['archived_harness']]
    require(all(str(path.relative_to(root)) in proofs for path in required), 'legacy core evidence missing')
    provenance = read(raw / 'provenance.json')
    require(sha(root / group['archived_harness']) == provenance['harness_sha256'],
            'legacy archived harness differs from the measured harness')
    rows = [json.loads(line) for line in (raw / 'results.jsonl').read_text().splitlines()]
    validate_records(root, group, provenance, rows, read(report_path))
    for row in rows:
        path = raw / ('%03d-%s-%s.json' % (row['ordinal'], row['variant'], row['case']))
        require(str(path.relative_to(root)) in proofs and read(path) == row,
                'legacy append ledger differs from final build receipt')
    source = root / '.work/sources' / project
    marker = read(source / '.rust-interp-owned.json')
    pin = provenance['project']['revision']
    require(marker['owner'] == str(root) and marker['revision'] == pin and
            subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=source, text=True).strip() == pin and
            not subprocess.check_output(['git', 'diff', '--name-only', 'HEAD'], cwd=source, text=True).strip(),
            'legacy source ownership, pin or restoration differs')
    process = subprocess.run(['ps', '-axo', 'pid,ppid,lstart,tty,command'], capture_output=True, text=True)
    require(process.returncode == 0 and not process.stderr, 'legacy process inspection failed')
    # The original controller predates supervisor receipts. Reject a current
    # controller naming this run or any process naming its exact target root.
    target_root = str(root / '.work/targets' / run / project)
    current = [line for line in process.stdout.splitlines()[1:]
               if target_root in line or ('bench.py' in line and '--run-id ' + run in line)]
    require(not current, 'legacy benchmark or cache user is still live')
    target = root / '.work/targets' / run / project / variant
    require(target.resolve(strict=True) == target and target.is_dir(), 'legacy target is noncanonical')
    verified = dict(kind='completed legacy native Cargo comparison', run_id=run, project=project,
        variant=variant, completed_commands=sum(row['variant'] == variant for row in rows),
        all_project_commands=len(rows), source_pin=pin, source_restored=True,
        preserved_evidence_files=len(proofs), performance_reassessed=False,
        note='Final on-disk cache contents are archived. Historical outcomes come from preserved completed commands; no byte identity with each historical executable or new guest-backend claim is made.')
    return target, proofs, verified
