"""Read closed scalar code and bound successful machine-CFG paths."""
import collections
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import time
from model import costs

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from compare_saved_runtime import acquire_lock, sha
from workflow_io import capture, require_space, write_json as write

NAME = 'scalar-path-costs-01'
RUNS = dict(store_log='scalar-store-log-profile-01', path='scalar-path-profile-01')


def main():
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45)
        require_space(ROOT, 12)
        frozen = {}
        def bind(path, expected=None):
            path = path.resolve(strict=True)
            key = str(path.relative_to(ROOT))
            digest = sha(path)
            if expected is not None:
                assert digest == expected, key
            assert key not in frozen or frozen[key] == digest
            frozen[key] = digest
            return json.loads(path.read_text()) if path.suffix == '.json' else None
        for path in [*Path(__file__).parent.glob('*.py'), Path(__file__).with_name('PLAN.md'),
                     ROOT/'scripts/compare_saved_runtime.py', ROOT/'scripts/workflow_io.py', ROOT/'scripts/supervise_experiment.py']:
            bind(path)
        summaries = {}
        for mode, run in RUNS.items():
            out = ROOT/'results'/run
            closure = bind(out/'closure.json')
            assert closure['status'] == 'closed' and closure['all_hashes_verified']
            summary = bind(out/'summary.json', closure['summary_sha256'])
            bind(out/'terminal.json', closure['terminal_sha256'])
            bind(ROOT/closure['bindings'], closure['bindings_sha256'])
            assert summary['status'] == 'passed' and summary['commands'] == 3
            assert summary['exact_per_pc_counts'] and summary['exact_logical_counts_memory_and_entropy']
            assert summary['exact_operation_map_reconstruction']
            summaries[mode] = summary
            for row in summary['comparisons']:
                if row['mode'] != 'candidate':
                    continue
                for kind in ['profile', 'code', 'operations']:
                    bind(ROOT/row[kind+'_path'], row[kind+'_sha256'])
                bind((ROOT/row['code_path']).with_name('map.json'), row['map_sha256'])
        work = ROOT/'.work'/NAME
        work.mkdir(exist_ok=False)
        revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
        assert not subprocess.check_output(['git', 'diff', '--name-only', 'HEAD'], cwd=ROOT).strip()
        write(work/'plan.json', dict(owner=str(ROOT), source_revision=revision, frozen=frozen,
                                   runs=RUNS, guest_commands=0, executable_code_publications=0))
        command = [sys.executable, '-m', 'unittest', '-v', 'test_model']
        start = time.time()
        child, stdout, stderr = capture(command, cwd=Path(__file__).parent, env=os.environ.copy(),
            receipt_path=work/'active.json', receipt=dict(label='controls'))
        for stream, value in [('stdout', stdout), ('stderr', stderr)]:
            (work/('controls.'+stream)).write_text(value)
        record = dict(command=command, pid=child.pid, returncode=child.returncode, seconds=time.time()-start,
                      stdout_sha256=sha(work/'controls.stdout'), stderr_sha256=sha(work/'controls.stderr'))
        write(work/'records.json', [record])
        assert child.returncode == 0 and 'Ran 8 tests' in stderr and stderr.rstrip().endswith('OK'), stderr
        cases = []
        for index in range(3):
            require_space(ROOT, 8)
            modes, metadata = {}, {}
            for mode, summary in summaries.items():
                row, = [r for r in summary['comparisons'] if r['index'] == index and r['mode'] == 'candidate']
                metadata[mode] = row
                profile = json.loads((ROOT/row['profile_path']).read_text())
                code = (ROOT/row['code_path']).read_bytes()
                operations = json.loads((ROOT/row['operations_path']).read_text())
                assert operations['code_sha256'] == row['code_sha256']
                assert operations['code_bytes'] == len(code) and operations['complete'] and operations['reconstructed_bytes_match']
                assert operations['profiled'] and operations['schema_version'] == 2
                at, bodies = 0, {}
                for f in operations['functions']:
                    assert f['offset'] == at and at < f['end'] <= len(code)
                    at = f['end']
                    if f['spans'][0]['kind'] != 'scalar_leaf':
                        continue
                    assert len(f['spans']) == 1 and f['spans'][0]['offset'] == f['offset'] and f['spans'][0]['end'] == f['end']
                    fid = f['function']; pf = profile['functions'][fid]
                    assert f['name'] == pf['name'] and fid not in bodies
                    assert len(pf['operations']) == len(pf['jit_scalar_hits'])
                    calls = sum(h for op, h in zip(pf['operations'], pf['jit_scalar_hits']) if op == 'Return')
                    body = code[f['offset']:f['end']]
                    assert len(body) % 4 == 0
                    try:
                        analysis = dict(status='passed', **costs([w for w, in struct.iter_unpack('<I', body)]))
                    except ValueError as exc:
                        analysis = dict(status='declined', reason=str(exc))
                    import hashlib
                    bodies[fid] = dict(function=fid, name=f['name'], successful_calls=calls,
                                       native_sha256=hashlib.sha256(body).hexdigest(), **analysis)
                assert at == len(code) and len(bodies) == row['scalar_bodies']
                assert sum(b['successful_calls'] for b in bodies.values()) == row['scalar_calls']
                modes[mode] = bodies
            assert metadata['path']['profile_sha256'] == metadata['store_log']['profile_sha256']
            common = sorted(modes['path'].keys() & modes['store_log'].keys())
            matched = []
            for fid in common:
                a, b = modes['store_log'][fid], modes['path'][fid]
                assert a['name'] == b['name'] and a['successful_calls'] == b['successful_calls']
                matched.append(dict(function=fid, name=a['name'], successful_calls=a['successful_calls'],
                                    changed=a['native_sha256'] != b['native_sha256'], store_log=a, path=b))
            cases.append(dict(index=index, matched=matched,
                unmatched={m: sorted(set(bodies)-set(common)) for m, bodies in modes.items()}))
            print('case', index, 'matched', len(common), 'changed', sum(r['changed'] for r in matched), flush=True)
        write(work/'details.json', cases)
        aggregates = []
        for case in cases:
            selected = [r for r in case['matched'] if r['changed'] and all(r[m]['status']=='passed' for m in RUNS)]
            weighted = {}
            for mode in RUNS:
                keys = sorted({key for r in selected for key in r[mode]['bounds']})
                weighted[mode] = {key: {end:sum(r['successful_calls']*r[mode]['bounds'].get(key, {}).get(end, 0) for r in selected)
                                       for end in ['min', 'max']} for key in keys}
            aggregates.append(dict(index=case['index'], matched_bodies=len(case['matched']),
                changed_bodies=sum(r['changed'] for r in case['matched']), analyzed_changed_bodies=len(selected),
                changed_successful_calls=sum(r['successful_calls'] for r in selected), weighted=weighted,
                declines={m:dict(collections.Counter(r[m]['reason'] for r in case['matched'] if r[m]['status']=='declined')) for m in RUNS},
                unmatched=case['unmatched']))
        assert all(sha(ROOT/p)==h for p,h in frozen.items())
        out = ROOT/'results'/NAME;out.mkdir(exist_ok=False)
        write(out/'summary.json',dict(status='passed', source_revision=revision, commands=1, controls=8,
            enumerated_oracle_graphs=512, cases=aggregates, raw=str(work.relative_to(ROOT)),
            plan_sha256=sha(work/'plan.json'),records_sha256=sha(work/'records.json'),details_sha256=sha(work/'details.json'),
            guest_commands=0, executable_code_publications=0, rust_builds=0, performance_measurement=False,
            scope='Conservative successful CFG-path bounds in two parked profiled scalar backends. Conditions are independent; no retired-instruction or speedup claim. Categories have independent extrema. Excludes failures, callers, ordinary fallbacks and preparation.'))
        print(json.dumps(aggregates),flush=True)


if __name__ == '__main__':
    main()
