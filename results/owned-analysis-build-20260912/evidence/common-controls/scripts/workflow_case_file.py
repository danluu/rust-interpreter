"""Load a bounded public workflow specification; values are data, never commands."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess


def require(ok, message):
    if not ok:
        raise ValueError('invalid workflow case: ' + message)


def checked(data, project, revision):
    require(isinstance(data, dict) and set(data) ==
            {'schema_version', 'label', 'project', 'revision', 'edit_class', 'case'}, 'unexpected top-level fields')
    require(type(data['schema_version']) is int and data['schema_version'] == 1, 'unsupported schema')
    require(project in {'fre', 'pgrust', 'nushell', 'ruff'} and data['project'] == project, 'public project differs')
    require(data['revision'] == revision, 'source pin differs')
    require(isinstance(data['label'], str) and re.fullmatch(r'[a-z0-9][a-z0-9-]{0,95}', data['label']), 'invalid label')
    require(isinstance(data['edit_class'], str) and re.fullmatch(r'[a-z][a-z0-9-]{0,95}', data['edit_class']), 'invalid edit class')
    case = data['case']
    require(isinstance(case, dict) and set(case) ==
            {'package', 'file', 'workload', 'tests', 'negative', 'edits', 'selections'}, 'unexpected case fields')
    require(isinstance(case['package'], str) and re.fullmatch(r'[A-Za-z0-9_-]{1,128}', case['package']), 'invalid package')
    name = case['file']
    require(isinstance(name, str) and 0 < len(name) <= 1024 and '\\' not in name and '\x00' not in name, 'invalid source path')
    path = PurePosixPath(name)
    require(not path.is_absolute() and str(path) == name and '..' not in path.parts and path.suffix == '.rs',
            'source path must be a normalized relative Rust file')
    require(isinstance(case['workload'], str) and 0 < len(case['workload']) <= 8192, 'invalid workload description')
    tests = case['tests']
    require(isinstance(tests, list) and 1 <= len(tests) <= 256 and
            all(isinstance(t, str) and 0 < len(t) <= 4096 and re.fullmatch(r'[A-Za-z0-9_:]+', t) for t in tests),
            'invalid test names')
    require(len(tests) == len(set(tests)), 'duplicate tests')
    edits = case['edits']
    require(isinstance(edits, list) and 1 <= len(edits) <= 30, 'invalid edit count')
    changes = [case['negative'], *edits]
    labels = []
    for change in changes:
        require(isinstance(change, list) and len(change) == 3 and all(isinstance(s, str) for s in change),
                'a replacement must contain label, before and after strings')
        label, before, after = change
        require(re.fullmatch(r'[a-z0-9][a-z0-9-]{0,95}', label), 'invalid replacement label')
        require(0 < len(before) <= 1024 * 1024 and len(after) <= 1024 * 1024 and before != after,
                'empty, unchanged or oversized replacement')
        labels.append(label)
    require(len(labels) == len(set(labels)), 'duplicate replacement labels')
    selections = case['selections']
    require(isinstance(selections, list) and len(selections) == len(edits), 'selection count differs')
    for selection in selections:
        require(isinstance(selection, list) and selection and
                all(type(n) is int and 0 <= n < len(tests) for n in selection), 'invalid selection index')
        require(len(selection) == len(set(selection)), 'duplicate selection indices')
    return case


def load(path, project, revision):
    path = Path(path).resolve(strict=True)
    require(path.is_file() and path.stat().st_size <= 8 * 1024 * 1024, 'case file exceeds 8 MiB or is not a file')
    raw = path.read_bytes()
    require(len(raw) <= 8 * 1024 * 1024, 'case file grew beyond 8 MiB')
    data = json.loads(raw)
    case = checked(data, project, revision)
    return case, dict(path=str(path), sha256=hashlib.sha256(raw).hexdigest(), label=data['label'],
                      edit_class=data['edit_class'], schema_version=data['schema_version'])


def source_file(source, case):
    """Check symlink resolution before a caller can mutate the selected file."""
    source = Path(source).resolve(strict=True)
    path = source / case['file']
    require(path.resolve(strict=True) == path and path.is_file() and path.is_relative_to(source),
            'source file escapes the snapshot or follows a symlink')
    return path


def verify_snapshot(root, report, rows):
    """Reconstruct the specified source states independently of captured hashes."""
    from workflow_measurements import initial_modes, source_states
    proof = report['case_file']
    snapshot = Path(root) / report['raw'] / 'case.json'
    require(proof['snapshot'] == str(snapshot.relative_to(root)), 'unexpected case snapshot path')
    revision = json.loads((Path(root) / 'benchmarks/corpus.json').read_text())['projects'][report['project']]['revision']
    require(report['revision'] == revision, 'report source pin differs')
    case, actual = load(snapshot, report['project'], revision)
    require(all(actual[k] == proof[k] for k in ['sha256', 'label', 'edit_class', 'schema_version']), 'case snapshot changed')
    require(report['workflow'] == actual['label'] and report['tests'] == case['tests'] and
            report['edits'] == [e[0] for e in case['edits']], 'case identity or selection differs')
    require(hashlib.sha256(json.dumps(case, sort_keys=True).encode()).hexdigest() == report['case_sha256'],
            'case content differs')
    source = Path(root) / '.work/sources' / report['project']
    original = subprocess.check_output(['git', 'show', revision + ':' + case['file']], cwd=source, text=True)
    modes = ['native', 'baseline', 'candidate'] if 'comparison' in report else ['native', 'interpreter', 'jit']
    modes = initial_modes(modes, report.get('initial_mode_order'))
    states = list(source_states(original, case, report['cycles'], modes, 'comparison' in report))
    expected = {(s['cycle'], s['state']): s for s in states}
    require(len(rows) == len(states) * len(modes), 'case command count differs')
    require([(r['cycle'], r['state'], r['mode']) for r in rows] ==
            [(s['cycle'], s['state'], mode) for s in states for mode in s['modes']],
            'captured case command sequence differs')
    for row in rows:
        state = expected[row['cycle'], row['state']]
        require(row['source_sha256'] == hashlib.sha256(state['source']).hexdigest(), 'case source state differs')
        tests = case['tests']
        if report['vary_selection'] and row['state'] > 0:
            tests = [tests[i] for i in case['selections'][row['state'] - 1]]
        require(row['tests'] == tests, 'case test selection differs')
    require(report['mode_orders'] == [{k: s[k] for k in ['cycle', 'state', 'phase', 'modes']} for s in states],
            'case mode rotation differs')
