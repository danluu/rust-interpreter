#!/usr/bin/env python3
"""Check public case validation and source-state preservation without compiling."""
import argparse
from copy import deepcopy
import fcntl
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from workflow_case_file import checked, load, source_file
from workflow_measurements import source_states


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    require(Path(args.run_id).name == args.run_id and args.run_id not in ['.', '..'], 'invalid run ID')
    lock = (ROOT / '.work/benchmark.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    cases = []
    paths = sorted(Path(__file__).parent.glob('*-*.json'))
    require(len(paths) == 2, 'unexpected interface case files')
    for path in paths:
        data = json.loads(path.read_text())
        case, record = load(path, data['project'], data['revision'])
        source = ROOT / '.work/sources' / data['project']
        original = subprocess.check_output(['git', 'show', 'HEAD:' + case['file']], cwd=source, text=True)
        require(subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=source, text=True).strip() == data['revision'],
                'case source pin differs')
        generated = list(source_states(original, case, 15, ['native', 'baseline', 'candidate'], True))
        require(len(generated) == 45 and len({s['source'] for s in generated}) == 3, 'incorrect interface source states')
        edited = [s for s in generated if s['state'] == 1]
        for mode in ['native', 'baseline', 'candidate']:
            require([sum(s['modes'].index(mode) == i for s in edited) for i in range(3)] == [5, 5, 5], 'unbalanced interface modes')
        marker = '\n#[cfg(test)]\nmod tests {'
        require(all(s['source'].decode().split(marker)[1] == original.split(marker)[1] for s in generated), 'original tests changed')
        cases.append(dict(case=record, states=len(generated), edited_pairs=len(edited), original_tests_unchanged=True,
                          source_hashes=sorted({hashlib.sha256(s['source']).hexdigest() for s in generated})))
    base = json.loads(paths[0].read_text())
    mutations = [
        ('absolute path', lambda d: d['case'].update(file='/tmp/outside.rs')),
        ('parent traversal', lambda d: d['case'].update(file='../outside.rs')),
        ('nested parent traversal', lambda d: d['case'].update(file='crates/../../outside.rs')),
        ('non-normalized path', lambda d: d['case'].update(file='./crates/file.rs')),
        ('wrong project', lambda d: d.update(project='rg-aot')),
        ('wrong revision', lambda d: d.update(revision='0' * 40)),
        ('boolean schema', lambda d: d.update(schema_version=True)),
        ('unknown field', lambda d: d['case'].update(command=['anything'])),
        ('duplicate tests', lambda d: d['case']['tests'].append(d['case']['tests'][0])),
        ('no edits', lambda d: d['case'].update(edits=[])),
        ('unchanged replacement', lambda d: d['case']['edits'][0].__setitem__(2, d['case']['edits'][0][1])),
        ('boolean selection', lambda d: d['case'].update(selections=[[True]])),
        ('out of range selection', lambda d: d['case'].update(selections=[[len(d['case']['tests'])]])),
        ('duplicate selection', lambda d: d['case'].update(selections=[[0, 0]])),
    ]
    rejected = []
    for label, mutate in mutations:
        changed = deepcopy(base)
        mutate(changed)
        try:
            checked(changed, base['project'], base['revision'])
        except ValueError as error:
            rejected.append(dict(case=label, error=str(error)))
        else:
            raise RuntimeError('unsafe or malformed case accepted: ' + label)
    with tempfile.TemporaryDirectory(prefix='interface-case-paths-', dir=ROOT / '.work') as folder:
        directory = Path(folder)
        source = directory / 'source'
        source.mkdir()
        (source / 'ordinary.rs').write_text('// path test\n')
        require(source_file(source, {'file': 'ordinary.rs'}) == source / 'ordinary.rs', 'ordinary source rejected')
        outside = directory / 'outside.rs'
        outside.write_text('// untouched\n')
        (source / 'linked.rs').symlink_to(outside)
        try:
            source_file(source, {'file': 'linked.rs'})
        except ValueError as error:
            rejected.append(dict(case='source symlink escape', error=str(error)))
        else:
            raise RuntimeError('source symlink escape accepted')
        require(outside.read_text() == '// untouched\n', 'outside file changed')
    out = ROOT / 'results' / args.run_id
    out.mkdir(exist_ok=False)
    frozen = [Path(__file__), ROOT / 'scripts/workflow_case_file.py', ROOT / 'scripts/workflow_measurements.py', *paths]
    summary = dict(status='passed', cases=cases, rejected=rejected,
                   frozen={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in frozen},
                   project_sources_mutated=False, compiled_or_executed=False, performance_measurement=False)
    (out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(dict(status='passed', cases=len(cases), malformed_cases_rejected=len(rejected))))


if __name__ == '__main__':
    main()
