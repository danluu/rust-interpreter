"""Qualify protocol labels and reconstruct four closed captures, without guests."""
from collections import Counter
import os
from pathlib import Path
import re
import subprocess
import sys
import time
ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'benchmarks/experiments/cross-program-template-model'))
import focus
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write
from workflow_measurements import child_usage,child_cpu_since
from summarize_owned_sample import parse_tree,self_samples
sys.path.insert(0,str(ROOT/'benchmarks/experiments/scalar-private-transfers'))
from native_observation import validate,locate
sys.path.insert(0,str(ROOT/'benchmarks/experiments/short-clear-tails'))
from qualify import admission,TARGET,BUILD
read = focus.read
RUN = 'current-call-protocol-01'
PREFIX = 'jit::code_spans::protocol_census::'
NAMES = [PREFIX+n for n in ['protocol_partitions_cover_copy_sizes_profiles_and_register_clearing',
    'protocol_partition_rejects_gaps_overlaps_missing_tail_and_argument_aliases',
    'scalar_protocol_partitions_preserve_complete_native_and_fallback_links']]


def derive(case,path):
    report = read(path);assert report['status'] == 'passed' and report['schema_version'] == 2
    assert report['exact_full_function_reconstruction'] and report['exact_transition_reconstruction'] and report['complete_partition']
    assert report['guest_commands'] == report['executable_code_publications'] == 0
    folder = ROOT/case['folder'];mapping = read(folder/'jit-code/operations.json')
    old = read(ROOT/case['report']);profile = read(ROOT/case['profile'])
    regions = read(folder/'jit-code/map.json');code = (folder/'jit-code/code.bin').read_bytes()
    record = read(folder/'record.json')
    assert report['code_sha256'] == sha(folder/'jit-code/code.bin')
    checked = validate(mapping,regions,code,profile,record['identity']['pid'])
    spans = report['spans'];fine = dict(rows=spans,starts=[s['offset'] for s in spans])
    assert fine['starts'] == sorted(set(fine['starts']))
    transitions = [r for r in checked['rows'] if r['kind'] == 'transition']
    assert len(transitions) == report['transitions']
    index = 0
    for row in transitions:
        cursor = row['offset']
        while index < len(spans) and spans[index]['offset'] < row['end']:
            span = spans[index]
            assert span['offset'] == cursor < span['end'] <= row['end']
            assert (span['function'],span['pc']) == (row['function'],row['pc'])
            assert row['label'] == 'transition:'+span['operation']
            assert span['kind'].startswith('argument_') == (span['argument'] is not None)
            cursor = span['end'];index += 1
        assert cursor == row['end']
    assert index == len(spans)
    counts,coarse_counts,sites,ambiguous = Counter(),Counter(),Counter(),[]
    for root in parse_tree((folder/'sample.txt').read_text()):
        for count,frame,_ in self_samples(root):
            if '<unknown binary>' not in frame: continue
            offsets = [int(a,16)-mapping['arena_base'] for a in re.findall(r'0x([0-9a-f]+)',frame)]
            if not offsets or not any(0 <= p < len(code) for p in offsets): continue
            assert '...' not in frame and all(0 <= p < len(code) for p in offsets)
            coarse = [locate(checked,p) for p in offsets]
            assert len({(r['function'],r['region_pc'],r['pc'],r['kind']) for r in coarse}) == 1
            if coarse[0]['kind'] != 'transition': continue
            label = coarse[0]['label'];coarse_counts[label] += count
            located = [locate(fine,p) for p in offsets]
            identities = {(r['operation'],r['kind'],r['argument']) for r in located}
            if len(identities) != 1:
                ambiguous.append(dict(count=count,frame=frame));continue
            op,kind,arg = next(iter(identities))
            counts[op+'/'+kind] += count
            sites[coarse[0]['function'],coarse[0]['pc'],op,kind,arg] += count
    expected = {k:old['by_label'][k] for k in ['transition:Call','transition:Return']}
    assert coarse_counts == expected
    total = sum(expected.values())
    assert sum(counts.values())+sum(r['count'] for r in ambiguous) == total
    static = Counter()
    for s in spans:static[s['operation']+'/'+s['kind']] += (s['end']-s['offset'])//4
    return dict(name=case['name'],generated_samples=old['attributed_generated_samples'],transition_samples=total,
        coarse_counts=dict(coarse_counts),fine_samples=dict(counts.most_common()),ambiguous=ambiguous,
        ambiguous_samples=sum(r['count'] for r in ambiguous),static_words=dict(static),
        scalar_bodies_reconstructed=report['scalar_bodies_reconstructed'],functions=report['functions'],
        transitions=report['transitions'],labels=len(spans),top_sites=[dict(function=fid,
            name=profile['functions'][fid]['name'][:200],pc=pc,operation=op,part=kind,argument=arg,samples=count)
            for (fid,pc,op,kind,arg),count in sites.most_common(30)])


def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);admission();frozen = {}
        def bind(p,expected=None):
            h = sha(p);assert expected is None or h == expected,p
            frozen[str(p.relative_to(ROOT))] = h
            return read(p) if p.suffix == '.json' else h
        folder = ROOT/'results/short-clear-tail-scope-01'
        closed = bind(folder/'closure.json');assert closed['status'] == 'closed' and closed['all_hashes_verified']
        previous = bind(folder/'summary.json',closed['summary_sha256'])
        terminal = bind(folder/'terminal.json',closed['terminal_sha256']);assert terminal['returncode'] == 0
        prior = bind(ROOT/previous['raw']/'plan.json',previous['plan_sha256'])
        for p,h in prior['frozen'].items():
            if p.startswith(('.work/','results/')):bind(ROOT/p,h)
        cases = []
        for i,case in enumerate(prior['cases']):
            report = bind(ROOT/case['report'])
            assert report['reconstructed_same_process_code'] and report['unassigned_generated_samples'] == 0
            for p,h in report['evidence'].items():bind(ROOT/p,h)
            sample_plan = bind((ROOT/case['folder']).parent/'plan.json')
            artifact = Path(sample_plan['artifact']);bind(artifact,sample_plan['artifact_sha256'])
            cases.append(dict(case,index=i,artifact=str(artifact.relative_to(ROOT))))
        assert len(cases) == 4
        paths = [ROOT/p for p in subprocess.check_output(['git','ls-files','crates','Cargo.toml','Cargo.lock','rust-toolchain.toml'],cwd=ROOT,text=True).splitlines()]
        paths += [*HERE.glob('*.py'),*HERE.glob('*.md'),Path(focus.__file__),BUILD/'owner.json',
            ROOT/'benchmarks/experiments/short-clear-tails/qualify.py',
            ROOT/'benchmarks/experiments/scalar-private-transfers/native_observation.py']
        paths += [ROOT/'scripts'/p for p in ['compare_saved_runtime.py','workflow_io.py','workflow_measurements.py','supervise_experiment.py','summarize_owned_sample.py']]
        for p in paths:bind(p)
        owner = read(BUILD/'owner.json');assert owner['owner'] == str(ROOT) and owner['target'] == str(TARGET)
        assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=ROOT).strip()
        revision = subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        raw = ROOT/'.work'/RUN;raw.mkdir(exist_ok=False);write(raw/'records.json',[])
        write(raw/'plan.json',dict(owner=str(ROOT),source_revision=revision,frozen=frozen,cases=cases,
            controller_command=[sys.executable,*sys.orig_argv[1:]],expected_commands=6,target=str(TARGET),
            target_purpose='bounded bytecode-test observer build; no new guest code execution',
            original_project_guest_commands=0,executable_code_publications=0,performance_measurement=False))
        env = {k:v for k,v in os.environ.items() if not k.startswith(('RUST_INTERP_','RUSTDEV_','CARGO_','PROTOCOL_')) and k not in
            ['RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','RUSTC','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER','RUST_TEST_THREADS','PYTHONPATH']}
        assert not any(k.startswith('DYLD_') for k in env)
        env.update(CARGO_INCREMENTAL='0',CARGO_PROFILE_RELEASE_DEBUG='1',CARGO_PROFILE_DEV_DEBUG='0',
            CARGO_PROFILE_TEST_DEBUG='0',RUST_TEST_THREADS='2',CARGO_TERM_COLOR='never',PYTHONDONTWRITEBYTECODE='1')
        common = ['--locked','--offline','--jobs','2','--manifest-path',str(ROOT/'Cargo.toml'),'--target-dir',str(TARGET),'-p','rust-interp-bytecode','--lib']
        commands = [(label,['cargo','+nightly-2026-09-08','test',*extra,*common,'--','--exact','--test-threads=2',*NAMES],{})
            for label,extra in [('debug',[]),('release',['--release'])]]
        for case in cases:
            output = raw/(str(case['index'])+'-protocol.json')
            commands.append((str(case['index']),['cargo','+nightly-2026-09-08','test','--release',*common,PREFIX+'observe_saved_protocol','--','--ignored','--exact','--test-threads=2'],
                dict(PROTOCOL_ARTIFACT=str(ROOT/case['artifact']),PROTOCOL_MAP=str(ROOT/case['folder']/'jit-code/operations.json'),
                    PROTOCOL_CODE=str(ROOT/case['folder']/'jit-code/code.bin'),PROTOCOL_OUTPUT=str(output))))
        records,comparisons = [],[]
        for label,cmd,extra in commands:
            current = admission();require_space(ROOT,8)
            assert all(sha(ROOT/p) == h for p,h in frozen.items())
            usage,start = child_usage(),time.perf_counter()
            child,out,err = capture(cmd,cwd=ROOT,env=env|extra,receipt_path=raw/(label+'-child.json'),receipt=dict(label=label))
            elapsed,cpu = time.perf_counter()-start,child_cpu_since(usage)
            for stream,value in [('stdout',out),('stderr',err)]: (raw/(label+'.'+stream)).write_text(value)
            paths = [raw/(label+'-child.json')]
            if extra:paths.append(Path(extra['PROTOCOL_OUTPUT']))
            records.append(dict(label=label,command=cmd,extra_env=extra,pid=child.pid,returncode=child.returncode,
                seconds=elapsed,cpu=cpu,admission=current,stdout_sha256=sha(raw/(label+'.stdout')),stderr_sha256=sha(raw/(label+'.stderr')),
                outputs={str(p.relative_to(ROOT)):sha(p) for p in paths if p.is_file()}))
            write(raw/'records.json',records);assert child.returncode == 0,(out+err)[-6000:]
            if label in ['debug','release']:
                assert 'test result: ok. 3 passed; 0 failed; 0 ignored;' in out
                assert all(name+' ... ok' in out for name in NAMES)
            else:
                assert 'test result: ok. 1 passed; 0 failed; 0 ignored;' in out
                comparisons.append(derive(cases[int(label)],raw/(label+'-protocol.json')))
                write(raw/'attribution.json',comparisons)
            records[-1]['after'] = admission();write(raw/'records.json',records)
            print(label,'protocol reconstruction/controls passed',flush=True)
        assert all(sha(ROOT/p) == h for p,h in frozen.items())
        result = ROOT/'results'/RUN;result.mkdir(exist_ok=False)
        write(result/'summary.json',dict(status='passed',source_revision=revision,raw=str(raw.relative_to(ROOT)),
            plan_sha256=sha(raw/'plan.json'),records_sha256=sha(raw/'records.json'),commands=6,tests_per_profile=3,
            comparisons=comparisons,setup_seconds=sum(r['seconds'] for r in records),setup_cpu_seconds=sum(r['cpu']['total_seconds'] for r in records),
            original_project_guest_commands=0,executable_code_publications=0,performance_measurement=False))


def close():
    raw = ROOT/'.work'/RUN;terminal = read(ROOT/'.work/experiments'/RUN/'status.json')
    assert terminal['status'] == 'finished'
    if terminal['returncode'] == 0:
        plan,records,summary = read(raw/'plan.json'),read(raw/'records.json'),read(ROOT/'results'/RUN/'summary.json')
        assert summary['commands'] == len(records) == 6 and summary['tests_per_profile'] == 3
        assert [derive(c,raw/(str(c['index'])+'-protocol.json')) for c in plan['cases']] == summary['comparisons']
        for r in records:
            for receipt in [r['admission'],r['after']]:
                assert receipt['allocated_target_bytes'] <= 3*1024**3
                assert receipt['required_free_bytes'] == max(14*1024**3,8*1024**3+2*receipt['allocated_target_bytes'])
                assert receipt['free_bytes'] >= receipt['required_free_bytes']
            child = read(raw/(r['label']+'-child.json'))
            assert child['status'] == 'finished' and child['returncode'] == r['returncode'] == 0
            assert child['pid'] == r['pid'] and child['parent_pid'] == terminal['child_pid'] and child['command'] == r['command']
            if r['label'] in ['debug','release']:
                out = (raw/(r['label']+'.stdout')).read_text()
                assert all(name+' ... ok' in out for name in NAMES)
                assert 'test result: ok. 3 passed; 0 failed; 0 ignored;' in out
    focus.RUN = RUN;focus.close()


if __name__ == '__main__':
    if sys.argv[1:] == ['--close']:close()
    else:
        assert len(sys.argv) == 1
        main()
