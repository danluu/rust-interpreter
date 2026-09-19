"""Paired entropy-controlled original tests for exact short-tail clearing."""
import importlib.util
import os
from pathlib import Path
import re
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'benchmarks/experiments/cross-program-template-model'))
import focus
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write
from interpreter import installed_tools
sys.path.insert(0,str(ROOT/'benchmarks/experiments/scalar-private-transfers'))
import native_observation as observer
spec = importlib.util.spec_from_file_location('short_tail_model',ROOT/'benchmarks/experiments/short-clear-tails/model.py')
model = importlib.util.module_from_spec(spec);spec.loader.exec_module(model)
read = focus.read
RUN = 'short-clear-tail-profile-01'
BASELINE = 'df4006e03daad7dd008eab34c24a03390d892ec14e55154c43e2d5568c0bba62'
OLD = model.OLD
NEW = struct.pack('<15I',*model.OLD_WORDS[:6],*model.TAIL)


def matches(code,pattern):
    return sum(code[i:i+len(pattern)] == pattern for i in range(0,len(code)-len(pattern)+1,4))


def compare(raw,case,records):
    profiles,results,maps = [],[],[]
    for mode in ['baseline','candidate']:
        label = str(case['index'])+'-'+mode
        row, = [r for r in records if r['label'] == label]
        assert row['returncode'] == 0 and (raw/(label+'.stdout')).read_text() == '0\n'
        err = (raw/(label+'.stderr')).read_text()
        selection, = [read_selection(line) for line in err.splitlines() if line.startswith('rust-interp-profile-selection: ')]
        for key in ['name','artifact_sha256','catalog_sha256']: assert selection[key] == case[key],key
        stats = {k:int(v) for k,v in re.findall(r'\b([a-z_]+)=(\d+)\b',err)}
        profile = read(raw/(label+'-profile.json'))
        _,totals = observer.logical_counts(profile)
        assert totals['total'] == stats['instructions'] and totals['native'] == stats['jit_instructions']
        dump = raw/(label+'-code')
        code,mapping,regions = (dump/'code.bin').read_bytes(),read(dump/'operations.json'),read(dump/'map.json')
        assert mapping['profiled'] and mapping['persistent_registers'] and mapping['resumable_calls']
        assert not mapping.get('indirect_calls',False)
        observed = observer.validate(mapping,regions,code,profile,row['pid'])
        assert stats['jit_declined_functions'] == 0 and stats['jit_bytes'] == len(code)
        pattern = OLD if mode == 'baseline' else NEW
        total = matches(code,pattern)
        assert total > 0 and matches(code,NEW if mode == 'baseline' else OLD) == 0
        spans = []
        for f in mapping['functions']:
            for span in f['spans']:
                data = code[span['offset']:span['end']]
                helpers = matches(data,pattern)
                if helpers:
                    assert span['kind'] == 'transition' and span['pc'] is not None
                    assert profile['functions'][f['function']]['operations'][span['pc']].startswith('Call ')
                spans.append((f['function'],span['kind'],span['pc'],span['region_pc'],len(data),helpers))
        assert sum(s[-1] for s in spans) == total
        maps.append(spans);profiles.append(profile)
        results.append(dict(mode=mode,statistics=stats,logical_counts=totals,helpers=total,
            native_code_bytes=len(code),mapped_spans=observed['spans']))
    totals = observer.exact_logical_counts(profiles[1],profiles[0])
    assert results[0]['logical_counts'] == results[1]['logical_counts'] == totals
    before,after = [r['statistics'] for r in results]
    assert {k:v for k,v in before.items() if k not in ['jit_compile_ns','jit_bytes']} == {
        k:v for k,v in after.items() if k not in ['jit_compile_ns','jit_bytes']},'VM counters changed'
    assert len(maps[0]) == len(maps[1])
    for a,b in zip(*maps):
        assert a[:4] == b[:4] and a[5] == b[5],(a,b)
        assert b[4]-a[4] == 20*a[5],(a,b)
    assert results[1]['native_code_bytes']-results[0]['native_code_bytes'] == 20*results[0]['helpers']
    return dict(index=case['index'],name=case['name'],runs=results,
        added_native_bytes=20*results[0]['helpers'],exact_per_pc_counts=True,
        exact_non_timing_counters=True,exact_span_growth=True)


def read_selection(line):
    import json
    return json.loads(line.split(': ',1)[1])


def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,12)
        frozen = {}
        def bind(p,expected=None):
            h = sha(p);assert expected is None or h == expected,p
            frozen[str(p.relative_to(ROOT))] = h
            return read(p) if p.suffix == '.json' else h
        def closed(name):
            folder = ROOT/'results'/name;c = bind(folder/'closure.json')
            assert c['status'] == 'closed' and c['all_hashes_verified']
            s = bind(folder/'summary.json',c['summary_sha256']);t = bind(folder/'terminal.json',c['terminal_sha256'])
            assert s['status'] == 'passed' and t['status'] == 'finished' and t['returncode'] == 0 and t['owner'] == str(ROOT)
            return s
        build = closed('short-clear-tail-workspace-02')
        assert build['tests'] == dict(python=dict(discovered=468,passed=446,skipped=22),
            debug=dict(passed=609,ignored=13),release=dict(passed=609,ignored=13))
        build_plan = bind(ROOT/build['raw']/'plan.json',build['plan_sha256'])
        for path,h in build_plan['frozen'].items():
            if path.startswith(('crates/','scripts/','tests/')) or path in ['Cargo.toml','Cargo.lock','rust-toolchain.toml']: bind(ROOT/path,h)
        candidate = ROOT/build['raw']/'rust-interp-vm';bind(candidate,build['outputs'][str(candidate.relative_to(ROOT))])
        tools,key = installed_tools(BASELINE);assert key == BASELINE
        baseline = tools/'rust-interp-vm'
        bind(baseline,'6ac4dd9e964e0ebb0a050f8412c8ec8877bd197e8ad7876832db378ed03ca7cf')
        current = closed('compact-switch-current-host-01')
        prior = bind(ROOT/current['raw']/'plan.json',current['plan_sha256'])
        library = Path(prior['library']);bind(library,prior['frozen'][str(library.relative_to(ROOT))])
        assert sha(library) == '8dcca07840e47041ecffaae85cae09ecde8c16d9ecc47b3bbc36816ae9909274'
        controls = closed('composed-native-sampler-protocol-01')
        proof = bind(ROOT/controls['raw']/'plan.json',controls['plan_sha256'])
        for path in ['benchmarks/experiments/scalar-private-transfers/native_observation.py',
            'benchmarks/experiments/scalar-private-transfers/test_native_observation.py']: bind(ROOT/path,proof['frozen'][path])
        scope = closed('short-clear-tail-scope-01')
        scope_plan = bind(ROOT/scope['raw']/'plan.json',scope['plan_sha256'])
        bind(Path(model.__file__),scope_plan['frozen'][str(Path(model.__file__).relative_to(ROOT))])
        history = closed('adopted-es8-edit-01')
        rows = bind(ROOT/history['raw']/'records.json',history['records_sha256'])
        row, = [r for r in rows if r['state'] == 'restored' and r['mode'] == 'custom']
        assert row['index'] == 31 and all(status == 'passed' for _,status in row['outcomes'])
        cases = []
        for name,_ in row['outcomes']:
            cases.append(dict(index=len(cases),name=name,artifact=row['artifact']['path'],artifact_sha256=row['artifact']['sha256'],
                catalog=row['catalog']['path'],catalog_sha256=row['catalog']['sha256'],
                limits=dict(instructions=100_000_000_000,allocations=150_000)))
        for old in prior['cases']:
            item = old['item']
            cases.append({**{k:item[k] for k in ['name','artifact','artifact_sha256','catalog','catalog_sha256','limits']},'index':len(cases)})
        assert len(cases) == 5
        for case in cases:
            for key in ['artifact','catalog']: bind(ROOT/case[key],case[key+'_sha256'])
        for p in [*HERE.glob('*.py'),*HERE.glob('*.md'),Path(focus.__file__)]: bind(p)
        assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=ROOT).strip()
        revision = subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        raw = ROOT/'.work'/RUN;raw.mkdir(exist_ok=False)
        write(raw/'plan.json',dict(owner=str(ROOT),source_revision=revision,frozen=frozen,cases=cases,
            controller_command=[sys.executable,*sys.orig_argv[1:]],expected_commands=10,original_project_guest_commands=10,
            vms=dict(baseline=str(baseline),candidate=str(candidate)),library=str(library),adopted_tool_key=BASELINE,
            vm_sha256=sha(candidate),performance_measurement=False,default_runtime_adoption=False))
        env = {k:v for k,v in os.environ.items() if not k.startswith(('RUST_INTERP_','RUSTDEV_'))}
        assert not any(k.startswith('DYLD_') for k in env)
        env.update(DYLD_INSERT_LIBRARIES=str(library),RUST_INTERP_VM_STATS='1')
        records,comparisons = [],[];write(raw/'records.json',records)
        for case in cases:
            tape = raw/(str(case['index'])+'.tape')
            for mode,vm in [('baseline',baseline),('candidate',candidate)]:
                require_space(ROOT,8);assert all(sha(ROOT/p) == h for p,h in frozen.items())
                label = str(case['index'])+'-'+mode
                command = [str(vm),'--engine','jit','--jit-resumable-calls','--jit-persistent-registers','--jit-scalar-calls',
                    '--jit-code-dump',str(raw/(label+'-code')),'--jit-operation-map','--profile',str(raw/(label+'-profile.json')),
                    '--profile-test',case['name'],'--suite-catalog',str(ROOT/case['catalog']),
                    '--instruction-limit',str(case['limits']['instructions']),'--allocation-limit',str(case['limits']['allocations']),str(ROOT/case['artifact'])]
                child,out,err = capture(command,cwd=ROOT,env=dict(env,RUST_INTERP_ENTROPY_TAPE=str(tape),
                    RUST_INTERP_ENTROPY_MODE='record' if mode == 'baseline' else 'replay'),
                    receipt_path=raw/(label+'-child.json'),receipt=dict(label=label))
                for stream,value in [('stdout',out),('stderr',err)]: (raw/(label+'.'+stream)).write_text(value)
                paths = [raw/(label+'-child.json'),raw/(label+'-profile.json'),tape,*((raw/(label+'-code')).glob('*'))]
                record = dict(label=label,command=command,pid=child.pid,returncode=child.returncode,
                    stdout_sha256=sha(raw/(label+'.stdout')),stderr_sha256=sha(raw/(label+'.stderr')),
                    outputs={str(p.relative_to(ROOT)):sha(p) for p in paths if p.is_file()})
                records.append(record);write(raw/'records.json',records)
                assert child.returncode == 0,(out+err)[-4000:]
                print(label,'original assertion returned success',flush=True)
            comparisons.append(compare(raw,case,records));write(raw/'comparisons.json',comparisons)
            print(case['index'],'exact counts/counters/native-span growth verified',flush=True)
        assert all(sha(ROOT/p) == h for p,h in frozen.items())
        result = ROOT/'results'/RUN;result.mkdir(exist_ok=False)
        write(result/'summary.json',dict(status='passed',source_revision=revision,raw=str(raw.relative_to(ROOT)),
            plan_sha256=sha(raw/'plan.json'),records_sha256=sha(raw/'records.json'),commands=10,original_project_guest_commands=10,
            comparisons=comparisons,vm_sha256=sha(candidate),adopted_tool_key=BASELINE,exact_per_pc_counts=True,
            exact_memory_and_entropy=True,exact_span_growth=True,performance_measurement=False,default_runtime_adoption=False))


def close():
    raw = ROOT/'.work'/RUN;terminal = read(ROOT/'.work/experiments'/RUN/'status.json')
    assert terminal['status'] == 'finished'
    if terminal['returncode'] == 0:
        plan,records,summary = read(raw/'plan.json'),read(raw/'records.json'),read(ROOT/'results'/RUN/'summary.json')
        assert len(records) == summary['commands'] == 10 and len(plan['cases']) == 5
        assert [compare(raw,c,records) for c in plan['cases']] == summary['comparisons']
        for r in records:
            child = read(raw/(r['label']+'-child.json'))
            assert child['status'] == 'finished' and child['returncode'] == r['returncode'] == 0
            assert child['pid'] == r['pid'] and child['parent_pid'] == terminal['child_pid'] and child['command'] == r['command']
            mode = r['label'].split('-')[1];assert r['command'][0] == plan['vms'][mode]
    focus.RUN = RUN;focus.close()


if __name__ == '__main__':
    if sys.argv[1:] == ['--close']: close()
    else:
        assert len(sys.argv) == 1
        main()
