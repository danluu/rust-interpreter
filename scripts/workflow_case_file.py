"""Load a bounded public workflow specification; values are data, never commands."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import re


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
