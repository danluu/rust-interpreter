"""Independent saved-file readback only; never imports the runner or starts a child."""
from pathlib import Path
import hashlib
import json
import os
import re
import resource
import stat
import time

ROOT = Path('/Users/danluu/dev/rust-interp-semantic-reuse-20260913')
SOURCE = ROOT/'experiments/proc-macro-arena-compiler-02'
OUT = ROOT/'results/proc-macro-arena-compiler-02'
WORK = ROOT/'.work/proc-macro-arena-compiler-02'
REPORT = Path('/Users/danluu/dev/rust-interp-oxc-native-baseline-20260918/.work/proc-macro-arena-compiler02-independent-readback-01.json')
FIELDS = ('dev', 'ino', 'mode', 'nlink', 'size', 'mtime_ns', 'ctime_ns')
START = time.monotonic()
rows = {}
resource.setrlimit(resource.RLIMIT_CPU, (60, 60))
resource.setrlimit(resource.RLIMIT_FSIZE, (2**20, 2**20))
resource.setrlimit(resource.RLIMIT_CORE, (0, 0))

def stamp(s):
    return {k: getattr(s, 'st_'+k) for k in FIELDS}

def record(path):
    path = Path(path)
    if str(path) in rows:
        assert stamp(path.lstat()) == rows[str(path)]['identity']
        return rows[str(path)]
    assert path.is_absolute() and path.resolve(strict=True) == path
    before = stamp(path.lstat())
    assert stat.S_ISREG(before['mode']) and before['size'] <= 512*2**20
    h = hashlib.sha256(); size = 0
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW), 'rb') as f:
        assert stamp(os.fstat(f.fileno())) == before
        while chunk := f.read(2**20):
            h.update(chunk); size += len(chunk)
            assert size <= 512*2**20 and time.monotonic()-START < 120
        assert stamp(os.fstat(f.fileno())) == before
    assert stamp(path.lstat()) == before and size == before['size']
    rows[str(path)] = {'sha256': h.hexdigest(), 'bytes': size, 'identity': before}
    assert len(rows) <= 256 and sum(r['bytes'] for r in rows.values()) <= 512*2**20
    return rows[str(path)]

def raw(path):
    r = record(path); assert r['bytes'] <= 2**20
    data = Path(path).read_bytes()
    assert hashlib.sha256(data).hexdigest() == r['sha256']
    assert stamp(Path(path).lstat()) == r['identity']
    return data

def read(path):
    return json.loads(raw(path))

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)

assert not REPORT.exists()
assert record(SOURCE/'run_once.py')['sha256'] == 'bf2387cdfa74970ab1a22cb185deff9bf70031703cbfddfaf016f94262424a04'
assert record(SOURCE/'plan.json')['sha256'] == '9c041b35bba1c23774e9da923556f232a6c7da3911256a0be124b2f638ae3593'
assert raw(SOURCE/'run_once.py') == raw(OUT/'run_once.py')
assert raw(SOURCE/'plan.json') == raw(OUT/'plan.json')
plan = read(OUT/'plan.json'); execution = read(OUT/'execution.json'); result = read(OUT/'result.json')
assert record(OUT/'result.json')['sha256'] == 'db87d2a204bd11f2c024a3e8132a04882706f0acd1a2fd46cdde540752e5f39f'
assert result['execution_sha256'] == record(OUT/'execution.json')['sha256']
assert execution['status'] == result['status'] == 'passed'
assert execution['compiler_children'] == result['compiler_children'] == len(plan['commands']) == 20
assert execution['signals'] == [] and execution['retries'] == 0
assert result['benchmark'] is False and result['compiler_distribution_qualified'] is False
assert execution['started_at'] <= execution['admitted_at'] < execution['finished_at'] <= execution['canonical_released_at']
assert execution['canonical_released_at']-execution['started_at'] < 2400
before = read(OUT/'inputs-before.json'); after = read(OUT/'inputs-after.json')
assert canonical(before) == canonical(after) and len(before) == 101
for name, expected in before.items():
    assert canonical(record(name)) == canonical(expected), name
assert before[str(SOURCE/'README.md')]['sha256'] == '531842e90e4e881df6245130813ff2a8bab5aac7056b1ac04abb5ff90bd33ac5'
for name, expected in plan['source_files'].items():
    assert record(name)['sha256'] == expected['sha256'] and record(name)['bytes'] == expected['bytes']
cases = {x['name']: x for x in plan['cases']}
expected_members = {'run_once.py','plan.json','execution.json','result.json','inputs-before.json','inputs-after.json','macro-dylibs.json'}
summaries = []; normalized = {}; pids = set(); previous_finish = execution['admitted_at']
for index, spec in enumerate(plan['commands']):
    label = f'{index:02d}-{spec["arm"]}-{spec.get("case", "dylib")}'
    expected_members.update(label+suffix for suffix in ['-record.json','-verification.json','.stdout','.stderr'])
    rec = read(OUT/(label+'-record.json')); saved = read(OUT/(label+'-verification.json'))
    assert canonical(rec) == canonical(execution['command_records'][index])
    assert rec['command'] == spec['argv'] and rec['environment'] == spec['environment'] and rec['cwd'] == spec['cwd']
    assert rec['status'] == 'closed' and rec['may_be_live'] is False and rec['observation_errors'] == []
    assert rec['parent_pid'] == execution['parent_pid'] and type(rec['pid']) is int and rec['pid'] > 0
    assert rec['pid'] not in pids; pids.add(rec['pid'])
    assert previous_finish <= rec['started_at'] <= rec['spawned_at'] <= rec['observation_finished_at'] <= rec['finished_at'] <= execution['finished_at']
    previous_finish = rec['finished_at']
    assert rec['finished_at']-rec['spawned_at'] <= spec['child_observer_seconds']
    assert rec['returncode'] == rec['expected_returncode'] == spec['expected_returncode']
    for stream in ['stdout','stderr']:
        assert canonical(record(OUT/(label+'.'+stream))) == canonical(rec[stream])
    assert raw(OUT/(label+'.stdout')) == b''
    messages = [json.loads(line) for line in raw(OUT/(label+'.stderr')).splitlines()]
    expected = [] if spec['role'] == 'build-macro-dylib' else list(cases[spec['case']]['errors'])
    primary_errors = []; abort_counts = []; stable = []
    for message in messages:
        assert message['$message_type'] == 'diagnostic'
        if message['level'] == 'error' and not message['spans']:
            match = re.fullmatch(r'aborting due to ([1-9][0-9]*) previous errors?', message['message'])
            assert match is not None; abort_counts.append(int(match[1])); continue
        if message['level'] != 'error':
            assert message['level'] == 'failure-note'; continue
        primary_errors.append(message)
        code = message['code']['code'] if message['code'] else None
        spans = [s for s in message['spans'] if s['is_primary']]
        matches = [x for x in expected if x['code'] == code and x['message'] == message['message']
                   and any(s['file_name'] == cases[spec['case']]['source'] and s['line_start'] == x['primary_line'] for s in spans)
                   and ('help' not in x or any(c['level'] == 'help' and c['message'] == x['help'] for c in message['children']))]
        assert len(matches) == 1; expected.remove(matches[0])
        stable.append({'level':'error','code':code,'message':message['message'],
            'primary_spans':[{k:s[k] for k in ['file_name','line_start','line_end','column_start','column_end']} for s in spans],
            'children':[{k:c[k] for k in ['level','message']} for c in message['children']]})
    assert not expected
    assert abort_counts == ([] if spec['expected_returncode'] == 0 else [len(primary_errors)])
    if spec['expected_returncode'] == 0:
        assert not messages
        assert canonical(record(spec['output'])) == canonical(saved['dependency']['output'])
        dep = dict(saved['dependency']['depinfo']); assert dep.pop('path') == spec['depinfo']
        assert canonical(record(spec['depinfo'])) == canonical(dep)
        text = raw(spec['depinfo']).decode()
        dependencies = set(text.replace('\\\n', ' ').split())
        if spec['role'] == 'caller':
            chosen = str(WORK/spec['arm']/'libarena04_macros.dylib')
            other = str(WORK/('stock' if spec['arm'] == 'candidate' else 'candidate')/'libarena04_macros.dylib')
            assert chosen in dependencies and other not in dependencies
        elif spec['arm'] == 'candidate':
            assert str(ROOT/'.work/proc-macro-arena-bridge-01/libproc_macro.rlib') in dependencies
            assert str(ROOT/'.work/proc-macro-arena-bridge-01/librustc_literal_escaper.rlib') in dependencies
            assert '/libproc_macro-9dac517e5d77c501.' not in text
        else:
            assert '/libproc_macro-9dac517e5d77c501.' in text
            assert str(ROOT/'.work/proc-macro-arena-bridge-01/libproc_macro.rlib') not in text
    else:
        assert not os.path.lexists(spec['output']) and saved['dependency'] == {'success_output_absent':True}
    stable.sort(key=lambda x:json.dumps(x,sort_keys=True))
    assert canonical(stable) == canonical(saved['diagnostics']) and saved['label'] == label
    if spec['role'] == 'caller':
        if spec['arm'] == 'stock': normalized[spec['case']] = stable
        else: assert canonical(stable) == canonical(normalized[spec['case']])
    summaries.append({'label':label,'pid':rec['pid'],'returncode':rec['returncode'],'errors':len(primary_errors)})
assert {p.name for p in OUT.iterdir()} == expected_members and len(expected_members) == 87
for path, expected in read(OUT/'macro-dylibs.json').items():
    assert canonical(record(path)) == canonical(expected)
work_files = [p for p in WORK.rglob('*') if p.is_file()]
assert len(work_files) <= 512 and sum(p.stat().st_size for p in work_files) == execution['work_bytes'] <= 128*2**20
for p in work_files: record(p)
for path, row in rows.items(): assert stamp(Path(path).lstat()) == row['identity']
report = {'status':'verified','created_at':time.time(),'reviewer_pid':os.getpid(),
    'reviewer_source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    'execution_sha256':record(OUT/'execution.json')['sha256'],'result_sha256':record(OUT/'result.json')['sha256'],
    'compiler_parent_pid':execution['parent_pid'],'canonical_released_at':execution['canonical_released_at'],
    'compiler_children':20,'compared_cases':9,'unchanged_input_files':101,'result_members':87,
    'all_raw_diagnostics_read':True,'unexpected_spanless_errors':0,'all_child_closures_verified':True,
    'stock_candidate_diagnostics_equal':True,'candidate_library_and_literal_linkage_verified':True,
    'installed_compiler_inputs_unchanged':True,'real_proc_macro_client_integration':True,
    'compiler_distribution_qualified':False,'benchmark':False,'commands':summaries,
    'readback_files':len(rows),'readback_bytes':sum(r['bytes'] for r in rows.values()),'files':rows}
data = (json.dumps(report,sort_keys=True,indent=2)+'\n').encode(); assert len(data) <= 2**20
with REPORT.open('xb') as f: f.write(data)
assert REPORT.read_bytes() == data
print(json.dumps({'report':str(REPORT),'sha256':hashlib.sha256(data).hexdigest(),'files':len(rows),'bytes':report['readback_bytes']}))
