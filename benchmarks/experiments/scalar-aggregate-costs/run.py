"""Read closed scalar code and bound successful machine-CFG paths."""
import collections
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import time
from model import costs, word_delta

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from compare_saved_runtime import acquire_lock, sha
from workflow_io import capture, require_space, write_json as write

NAME = 'scalar-aggregate-costs-02'
RUNS = dict(control='scalar-aggregate-profile-01', candidate='scalar-aggregate-profile-01')


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
                if row['mode'] != mode:
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
        command = [sys.executable, '-m', 'unittest', '-v', 'test_paths', 'test_delta']
        start = time.time()
        child, stdout, stderr = capture(command, cwd=Path(__file__).parent, env=os.environ.copy(),
            receipt_path=work/'active.json', receipt=dict(label='controls'))
        for stream, value in [('stdout', stdout), ('stderr', stderr)]:
            (work/('controls.'+stream)).write_text(value)
        record = dict(command=command, pid=child.pid, returncode=child.returncode, seconds=time.time()-start,
                      stdout_sha256=sha(work/'controls.stdout'), stderr_sha256=sha(work/'controls.stderr'))
        write(work/'records.json', [record])
        assert child.returncode == 0 and 'Ran 14 tests' in stderr and stderr.rstrip().endswith('OK'), stderr
        cases = []
        for index in range(3):
            require_space(ROOT, 8)
            modes, metadata = {}, {}
            for mode, summary in summaries.items():
                row, = [r for r in summary['comparisons'] if r['index'] == index and r['mode'] == mode]
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
                                       native_sha256=hashlib.sha256(body).hexdigest(), words=[w for w, in struct.iter_unpack('<I', body)], **analysis)
                assert at == len(code) and len(bodies) == row['scalar_bodies']
                assert sum(b['successful_calls'] for b in bodies.values()) == row['scalar_calls']
                modes[mode] = bodies
            common = sorted(modes['control'].keys() & modes['candidate'].keys())
            matched = []
            for fid in common:
                a, b = modes['control'][fid], modes['candidate'][fid]
                assert a['name'] == b['name'] and a['successful_calls'] == b['successful_calls']
                matched.append(dict(function=fid, name=a['name'], successful_calls=a['successful_calls'],
                    changed=a['native_sha256'] != b['native_sha256'],
                    delta=word_delta(a['words'],b['words']),
                    control={k:v for k,v in a.items() if k!='words'},candidate={k:v for k,v in b.items() if k!='words'}))
            added=[{k:v for k,v in modes['candidate'][fid].items() if k!='words'}
                   for fid in sorted(modes['candidate'].keys()-modes['control'].keys())]
            removed=sorted(modes['control'].keys()-modes['candidate'].keys())
            assert not removed
            cases.append(dict(index=index,matched=matched,added=added,removed=removed))
            print('case',index,'common',len(common),'added',len(added),flush=True)
        write(work/'details.json', cases)
        aggregates=[]
        for case in cases:
            common=case['matched'];added=case['added']
            aggregates.append(dict(index=case['index'],common_bodies=len(common),
                common_successful_calls=sum(r['successful_calls'] for r in common),
                identical_bodies=sum(r['delta']['equal_words'] for r in common),
                changed_word_count=sum(not r['delta']['same_word_count'] for r in common),
                offset_only_changed_bodies=sum(bool(r['delta']['shifted_sp_accesses']) and not r['delta']['other_changes'] for r in common),
                changed_sp_access_sites=sum(len(r['delta']['shifted_sp_accesses']) for r in common),
                other_changed_sites=sum(len(r['delta']['other_changes']) for r in common),
                added=added,added_successful_calls=sum(r['successful_calls'] for r in added)))
        assert all(sha(ROOT/p)==h for p,h in frozen.items())
        out = ROOT/'results'/NAME;out.mkdir(exist_ok=False)
        write(out/'summary.json',dict(status='passed', source_revision=revision, commands=1, controls=14,
            enumerated_oracle_graphs=512, cases=aggregates, raw=str(work.relative_to(ROOT)),
            plan_sha256=sha(work/'plan.json'),records_sha256=sha(work/'records.json'),details_sha256=sha(work/'details.json'),
            guest_commands=0, executable_code_publications=0, rust_builds=0, performance_measurement=False,
            scope='Descriptive common-body opcode comparison and conservative added-body successful CFG bounds. Profiled code; no timing, equivalence, cache or hardware-cycle inference. Excludes failures, callers, ordinary fallbacks and preparation.'))
        print(json.dumps([{k:v for k,v in r.items() if k!='added'} for r in aggregates]),flush=True)


if __name__ == '__main__':
    main()
