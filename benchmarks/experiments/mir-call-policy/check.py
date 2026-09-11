#!/usr/bin/env python3
"""Reproduce actual runtime receipts and exercise explicit compiler-policy fixtures."""
import copy
import fcntl
import hashlib
import json
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
import verify_repeated_workflow as verifier
from verify_repeated_workflow import require

FLAGS = dict(baseline=['-Zmir-opt-level=3'], candidate=['-Zmir-opt-level=3',
    '-Zinline-mir-threshold=400', '-Zinline-mir-hint-threshold=800', '-Zinline-mir-forwarder-threshold=240'])


def main():
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        actual = []
        for run in ['resumable-copy-e2e-01', 'resumable-copy-original-e2e-01', 'resumable-bulk-e2e-02']:
            for label in ['folded-literal-trie', 'token-phrase']:
                p = ROOT / 'results' / f'{run}-{label}' / 'summary.json'
                report = verifier.read(p)
                require(verifier.verify(report) == verifier.read(p.with_name('verification.json')), 'historical receipt changed')
                actual.append(str(p.relative_to(ROOT)))
        p = ROOT / actual[0]
        report = verifier.read(p)
        records_path = ROOT / report['raw'] / 'records.json'
        rows = verifier.read(records_path)
        # Synthetic control fixtures only. Actual historical receipts remain untouched.
        report['comparison']['identical_bytecode_required'] = False
        report['tool_builds']['baseline'] = copy.deepcopy(report['tool_builds']['candidate'])
        for mode in FLAGS:
            report['tool_builds'][mode]['guest_rustflags'] = FLAGS[mode]
        for row in rows:
            if row['mode'] == 'native': continue
            for call in row['calls']:
                call['rustflags'] = ' '.join(FLAGS[row['mode']])
                call['launch']['tool_key'] = report['tool_builds'][row['mode']]['tool_key']
        read = verifier.read
        def check(r=report, records=rows, flags=FLAGS):
            with patch.object(verifier, 'read', side_effect=lambda path: records if path == records_path else read(path)):
                return verifier.verify(r, compiler_flags=flags)
        require(check()['paired_bytecode_identical'], 'equal-artifact compiler fixture failed')
        changed = copy.deepcopy(rows)
        baseline = [r for r in changed if r['mode'] == 'baseline']
        baseline[0]['artifacts'], baseline[1]['artifacts'] = baseline[1]['artifacts'], baseline[0]['artifacts']
        require(not check(records=changed)['paired_bytecode_identical'], 'different artifacts falsely claimed equal')
        try: check(records=changed, flags=None)
        except RuntimeError as error: require(str(error) == 'paired bytecode differs', 'unexpected default rejection')
        else: raise RuntimeError('default runtime verification accepted different artifacts')
        rejected = ['default rejects different artifacts']
        def reject(name, mutate, expected):
            r, rs, flags = copy.deepcopy(report), copy.deepcopy(rows), copy.deepcopy(FLAGS)
            mutate(r, rs, flags)
            try: check(r, rs, flags)
            except RuntimeError as error: require(str(error) == expected, f'{name}: unexpected rejection {error}')
            else: raise RuntimeError(name + ': invalid fixture accepted')
            rejected.append(name)
        reject('one expected mode', lambda r, rs, f: f.pop('baseline'), 'compiler comparison requires explicit flags for both modes')
        reject('equal flags', lambda r, rs, f: f.update(baseline=f['candidate']), 'invalid compiler comparison flags')
        reject('empty flag', lambda r, rs, f: f['baseline'].append(''), 'invalid compiler comparison flags')
        reject('whitespace flag', lambda r, rs, f: f['baseline'].append('-Zfoo bar'), 'invalid compiler comparison flags')
        reject('required equality', lambda r, rs, f: r['comparison'].update(identical_bytecode_required=True), 'compiler comparison cannot waive a required artifact match')
        reject('claimed flags', lambda r, rs, f: r['tool_builds']['baseline'].update(guest_rustflags=['wrong']), 'compiler flags differ from the independent expectation')
        for field, value in [('tool_key', 'other'), ('vm_sha256', 'other'), ('exporter_sha256', 'other'), ('jit_resumable_calls', False), ('inline_leaves', False)]:
            reject('changed ' + field, lambda r, rs, f, k=field, v=value: r['tool_builds']['baseline'].update({k:v}), 'compiler comparison changed tools or runtime options')
        index = next(i for i, r in enumerate(rows) if r['mode'] == 'baseline')
        reject('executed flags', lambda r, rs, f: rs[index]['calls'][0].update(rustflags='wrong'), 'executed compiler flags or tool differ')
        reject('executed tool', lambda r, rs, f: rs[index]['calls'][0]['launch'].update(tool_key='wrong'), 'executed compiler flags or tool differ')
        reject('artifact corruption', lambda r, rs, f: rs[index]['artifacts'][0].update(sha256='wrong'), 'artifact hash mismatch')
        reject('missing command', lambda r, rs, f: rs.pop(), 'command order differs from schedule')
        reject('wrong edit accepted', lambda r, rs, f: r.update(wrong_production_edit_rejected=False), 'source/test controls failed')
        reject('test source changed', lambda r, rs, f: r.update(test_source_unchanged=False), 'source/test controls failed')
        out = ROOT / 'results/mir-call-policy-controls-01'
        out.mkdir(exist_ok=False)
        paths = [Path(__file__), ROOT / 'scripts/verify_repeated_workflow.py', Path(__file__).with_name('PLAN.md')]
        result = dict(status='passed', actual_reports=actual, positive_compiler_fixtures=2, rejected=rejected,
            synthetic_fixtures_are_performance_evidence=False, historical_files_modified=False,
            sources={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})
        (out / 'summary.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(dict(actual_reports=len(actual), positive_compiler_fixtures=2, rejected=len(rejected))))


if __name__ == '__main__': main()
