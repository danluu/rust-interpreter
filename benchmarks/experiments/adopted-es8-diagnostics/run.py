"""Four bounded original-test diagnostics; reuse qualified observation tools."""
from collections import Counter
import json
import os
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'benchmarks/experiments/adopted-es8-workflow'))
from common import inputs, revision, focus, read, sha, write, capture, acquire_lock, require_space
from model import KEY, NAMES, INSTRUCTIONS, ALLOCATIONS
from interpreter import installed_tools
sys.path.insert(0,str(ROOT/'benchmarks/experiments/scalar-runtime-sampling'))
from attribute import attribute
from native_observation import validate, logical_counts

RUN = 'adopted-es8-diagnostics-01'
VM = '6ac4dd9e964e0ebb0a050f8412c8ec8877bd197e8ad7876832db378ed03ca7cf'


def derive(profile_path, dump, stats, pid):
    profile = read(profile_path)
    counts, totals = logical_counts(profile)
    assert totals['total'] == stats['instructions'] and totals['native'] == stats['jit_instructions']
    mapping, native = read(dump/'operations.json'), read(dump/'map.json')
    assert mapping['profiled'] is True and mapping['persistent_registers'] and mapping['resumable_calls']
    assert not mapping.get('indirect_calls',False)
    observed = validate(mapping, native, (dump/'code.bin').read_bytes(), profile, pid)
    assert native['code_bytes'] == stats['jit_bytes'] and stats['jit_declined_functions'] == 0
    operations, functions = Counter(), []
    for fid,(function,hits) in enumerate(zip(profile['functions'],counts)):
        by_kind = Counter()
        for op,count in zip(function['operations'],hits):
            by_kind[op.split(' ',1)[0]] += count
        operations.update(by_kind)
        if sum(hits):
            functions.append(dict(function=fid,name=function['name'],instructions=sum(hits),
                operations=dict(by_kind.most_common()),frame_size=function['frame_size'],registers=function['registers']))
    return dict(logical_counts=totals,operations=dict(operations.most_common()),
        top_functions=sorted(functions,key=lambda r:r['instructions'],reverse=True)[:25],
        mapped_spans=observed['spans'],static_words=observed['static_words'])


def main():
    frozen, original, owner = inputs()
    def bind(path, expected=None):
        digest = sha(path)
        assert expected is None or digest == expected, path
        frozen[str(path.relative_to(ROOT))] = digest
        return read(path) if path.suffix == '.json' else digest
    def closed(name):
        folder = ROOT/'results'/name
        receipt = bind(folder/'closure.json')
        assert receipt['status'] == 'closed' and receipt['all_hashes_verified']
        summary = bind(folder/'summary.json',receipt['summary_sha256'])
        terminal = bind(folder/'terminal.json',receipt['terminal_sha256'])
        assert summary['status'] == 'passed' and terminal['returncode'] == 0
        return summary
    history = closed('adopted-es8-edit-01')
    assert history['tool_key'] == KEY and history['commands'] == 32 and history['strict_controls'] == 2
    assert history['source_restored'] and history['exact_native_test_outcomes'] and history['matching_custom_artifacts']
    old = ROOT/history['raw']
    bind(old/'plan.json',history['plan_sha256'])
    rows = bind(old/'records.json',history['records_sha256'])
    row, = [r for r in rows if r['state'] == 'restored' and r['mode'] == 'custom']
    assert row['index'] == 31 and row['outcomes'] == [[n,'passed'] for n in NAMES]
    artifact, catalog = [ROOT/row[k]['path'] for k in ['artifact','catalog']]
    for field in ['artifact','catalog','selection']:
        bind(ROOT/row[field]['path'],row[field]['sha256'])
    controls = closed('vmmap-label-compatibility-01')
    assert controls['attribution_tests'] == 9 and controls['retained_reports'] == 14 and controls['guest_commands'] == 0
    bind(ROOT/controls['raw']/'plan.json',controls['plan_sha256'])
    current = closed('composed-native-sampler-protocol-01')
    assert current['attribution_tests'] == 11 and current['retained_maps'] == 14
    assert current['invalid_cli_rejections'] == 2 and current['new_guest_commands'] == 0
    proof = bind(ROOT/current['raw']/'plan.json',current['plan_sha256'])
    dependencies = ['scripts/sample_owned_vm.py','scripts/summarize_owned_sample.py','scripts/vmmap_ranges.py',
        'benchmarks/experiments/scalar-runtime-sampling/attribute.py',
        'benchmarks/experiments/scalar-runtime-sampling/test_attribution.py',
        'benchmarks/experiments/scalar-private-transfers/native_observation.py',
        'benchmarks/experiments/scalar-private-transfers/test_native_observation.py',
        'benchmarks/experiments/operation-map/attribute.py','benchmarks/experiments/operation-map/maps.py']
    for p in dependencies:
        bind(ROOT/p,proof['frozen'][p])
    for p in HERE.iterdir():
        if p.suffix in ['.py','.md']: bind(p)
    tools,key = installed_tools(KEY)
    assert key == KEY and sha(tools/'rust-interp-vm') == VM
    source = revision()
    raw = ROOT/'.work'/RUN
    raw.mkdir(exist_ok=False)
    cases = []
    for i,name in enumerate(NAMES):
        profile = raw/(str(i)+'-profile.json')
        dump = raw/(str(i)+'-code')
        sample = 'adopted-es8-sample-'+str(i)+'-01'
        assert not (ROOT/'.work'/sample).exists() and not (ROOT/'results'/sample).exists()
        cmd = [tools/'rust-interp-vm','--engine','jit','--jit-resumable-calls','--jit-persistent-registers',
            '--jit-scalar-calls','--jit-code-dump',dump,'--jit-operation-map','--profile',profile,'--profile-test',name,
            '--suite-catalog',catalog,'--instruction-limit',str(INSTRUCTIONS),'--allocation-limit',str(ALLOCATIONS),artifact]
        sample_cmd = [sys.executable,ROOT/'scripts/sample_owned_vm.py','--tool-key',KEY,'--artifact',artifact,
            '--artifact-sha256',row['artifact']['sha256'],'--run-id',sample,'--repetitions','1','--duration','3',
            '--instruction-limit',str(INSTRUCTIONS),'--allocation-limit',str(ALLOCATIONS),
            '--jit-resumable-calls','--jit-persistent-registers','--jit-scalar-calls','--dump-code','--jit-operation-map',
            '--select-test',name,'--suite-catalog',catalog,'--lock-wait-seconds','45',
            '--minimum-free-bytes',str(8*1024**3),'--expected-jit-declines','0']
        cases.append(dict(index=i,name=name,profile=str(profile.relative_to(ROOT)),dump=str(dump.relative_to(ROOT)),
            profile_command=list(map(str,cmd)),sample_run=sample,sample_command=list(map(str,sample_cmd)),
            summary_command=[sys.executable,str(ROOT/'scripts/summarize_owned_sample.py'),'--run-id',sample]))
    write(raw/'plan.json',dict(owner=str(ROOT),source_revision=source,frozen=frozen,
        controller_command=[sys.executable,*sys.orig_argv[1:]],tool_key=KEY,vm_sha256=VM,cases=cases,
        artifact=row['artifact'],catalog=row['catalog'],expected_commands=6,original_project_guest_commands=4,
        minimum_child_gib=8,initial_minimum_gib=12,ordinary_entropy=True,performance_measurement=False))
    records, profiles, samples = [], [], []
    write(raw/'records.json',records)
    env = {k:v for k,v in os.environ.items() if not k.startswith(('RUST_INTERP_','RUSTDEV_'))}
    assert not any(k.startswith('DYLD_') for k in env)
    env.update(RUST_INTERP_VM_STATS='1',PYTHONDONTWRITEBYTECODE='1')
    def invoke(label,cmd):
        require_space(ROOT,8)
        assert all(sha(ROOT/p) == h for p,h in frozen.items())
        child,out,err = capture(cmd,cwd=ROOT,env=env,receipt_path=raw/(label+'-child.json'),receipt=dict(label=label))
        for stream,value in [('stdout',out),('stderr',err)]: (raw/(label+'.'+stream)).write_text(value)
        record = dict(label=label,command=cmd,pid=child.pid,returncode=child.returncode,
            stdout_sha256=sha(raw/(label+'.stdout')),stderr_sha256=sha(raw/(label+'.stderr')))
        retained = [raw/(label+'-child.json')]
        if label.startswith('profile-'):
            retained += [Path(cmd[cmd.index('--profile')+1])]
            retained += list(Path(cmd[cmd.index('--jit-code-dump')+1]).glob('*'))
        elif label.startswith('sample-'):
            retained += list((ROOT/'.work'/cmd[cmd.index('--run-id')+1]).rglob('*'))
        record['outputs'] = {str(p.relative_to(ROOT)):sha(p) for p in retained if p.is_file()}
        records.append(record)
        write(raw/'records.json',records)
        assert child.returncode == 0, err[-4000:]
        return record,out,err
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45)
        require_space(ROOT,12)
        for case in cases:
            i = case['index']
            record,out,err = invoke('profile-'+str(i),case['profile_command'])
            assert out == '0\n'
            selection, = [json.loads(l.split(': ',1)[1]) for l in err.splitlines() if l.startswith('rust-interp-profile-selection: ')]
            assert selection['name'] == case['name'] and selection['artifact_sha256'] == row['artifact']['sha256']
            assert selection['catalog_sha256'] == row['catalog']['sha256']
            stats = {k:int(v) for k,v in re.findall(r'\b([a-z_]+)=(\d+)\b',err)}
            result = derive(ROOT/case['profile'],ROOT/case['dump'],stats,record['pid'])
            profiles.append(dict(index=i,name=case['name'],statistics=stats,**result))
            write(raw/'records.json',records)
            write(raw/'profiles.json',profiles)
            print('profile',i,'validated',flush=True)
    # The existing sampler owns its own shared-lock admission; no nested lock.
    for case in cases:
        invoke('sample-'+str(case['index']),case['sample_command'])
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45)
        require_space(ROOT,8)
        for case in cases:
            invoke('summary-'+str(case['index']),case['summary_command'])
            sample = ROOT/'.work'/case['sample_run']
            plan = read(sample/'plan.json')
            assert plan['selection']['name'] == case['name'] and plan['vm_sha256'] == VM
            assert plan['repetitions'] == 1 and plan['sample_seconds'] == 3 and plan['expected_jit_declines'] == 0
            report = attribute(case['sample_run'],ROOT/case['profile'],VM)
            samples.append(dict(index=case['index'],name=case['name'],**report))
            print('sample',case['index'],report['by_label'],flush=True)
        assert all(sha(ROOT/p) == h for p,h in frozen.items())
        outputs = {str(p.relative_to(ROOT)):sha(p) for p in raw.rglob('*') if p.is_file()}
        for case in cases:
            for folder in [ROOT/'.work'/case['sample_run'],ROOT/'results'/case['sample_run']]:
                outputs.update({str(p.relative_to(ROOT)):sha(p) for p in folder.rglob('*') if p.is_file()})
        result = ROOT/'results'/RUN
        result.mkdir(exist_ok=False)
        write(result/'summary.json',dict(status='passed',source_revision=source,raw=str(raw.relative_to(ROOT)),
            plan_sha256=sha(raw/'plan.json'),records_sha256=sha(raw/'records.json'),commands=6,
            original_project_guest_commands=4,tool_key=KEY,vm_sha256=VM,ordinary_entropy=True,
            profiles=profiles,samples=samples,outputs=outputs,performance_measurement=False))


def close():
    raw = ROOT/'.work'/RUN
    terminal = read(ROOT/'.work/experiments'/RUN/'status.json')
    assert terminal['status'] == 'finished'
    if terminal['returncode'] == 0:
        plan,summary,records = read(raw/'plan.json'),read(ROOT/'results'/RUN/'summary.json'),read(raw/'records.json')
        assert summary['tool_key'] == KEY and summary['vm_sha256'] == VM and summary['original_project_guest_commands'] == 4
        assert summary['commands'] == len(records) == 6 and len(summary['profiles']) == len(summary['samples']) == 2
        for case,profile in zip(plan['cases'],summary['profiles']):
            record, = [r for r in records if r['label'] == 'profile-'+str(case['index'])]
            assert record['command'] == case['profile_command']
            err = (raw/(record['label']+'.stderr')).read_text()
            stats = {k:int(v) for k,v in re.findall(r'\b([a-z_]+)=(\d+)\b',err)}
            assert profile == dict(index=case['index'],name=case['name'],statistics=stats,
                **derive(ROOT/case['profile'],ROOT/case['dump'],stats,record['pid']))
            for kind in ['sample','summary']:
                record, = [r for r in records if r['label'] == kind+'-'+str(case['index'])]
                assert record['command'] == case[kind+'_command']
            sample, = read(ROOT/'.work'/case['sample_run']/'records.json')
            assert sample['identity']['status'] == 'finished' and sample['identity']['returncode'] == 0
            assert sample['statistics']['jit_declined_functions'] == 0 and sample['mapped']
            assert all(sha(ROOT/'.work'/case['sample_run']/'0'/p) == h for p,h in sample['files'].items())
            report = read(ROOT/'results'/case['sample_run']/'operation-attribution.json')
            assert report['reconstructed_same_process_code'] and report['profile_used_for_static_identity_only']
            assert not report['performance_measurement'] and report['attributed_generated_samples'] > 0
            assert all(sha(ROOT/p) == h for p,h in report['evidence'].items())
    focus.RUN = RUN
    focus.close()


if __name__ == '__main__':
    if sys.argv[1:] == ['--close']: close()
    else:
        assert len(sys.argv) == 1
        main()
