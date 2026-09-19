"""Qualify typed scalar entry invariants and scope exact saved protocol PCs."""
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
RUN = 'scalar-entry-empty-work-01'
PREFIX = 'jit::code_spans::scalar_entry_scope::'
NAMES = [PREFIX+n for n in ['empty_padding_proof_matches_retained_alignment_histories_and_rejects_missing_hypotheses',
    'positive_scalar_budget_guard_subsumes_only_the_common_zero_budget_check']]


def derive(case,path):
    typed = read(path);assert typed['status'] == 'passed'
    assert typed['artifact_sha256'] == sha(ROOT/case['artifact'])
    assert typed['protocol_sha256'] == sha(ROOT/case['protocol'])
    protocol = read(ROOT/case['protocol'])
    assert typed['code_sha256'] == protocol['code_sha256']
    assert typed['guest_commands'] == typed['executable_code_publications'] == 0
    sites = {(r['caller'],r['pc']):r for r in typed['sites']}
    assert len(sites) == len(typed['sites']) > 0
    expected = {(r['function'],r['pc']) for r in protocol['spans'] if r['kind'] == 'scalar_entry_budget'}
    assert set(sites) == expected
    for r in sites.values():
        assert r['zero_entry_check_subsumed'] and 0 < r['maximum_steps'] <= 512
        assert r['minimum_scalar_budget'] == r['maximum_steps']+1
        assert r['padding_proven_empty'] == (r['caller_frame_align'] >= r['callee_frame_align'] and max(r['caller_frame_size'],1)%r['callee_frame_align'] == 0)
    folder = ROOT/case['folder'];mapping = read(folder/'jit-code/operations.json')
    code = (folder/'jit-code/code.bin').read_bytes();regions = read(folder/'jit-code/map.json')
    profile = read(ROOT/case['profile']);record = read(folder/'record.json')
    checked = validate(mapping,regions,code,profile,record['identity']['pid'])
    fine = dict(rows=protocol['spans'],starts=[r['offset'] for r in protocol['spans']])
    counts,ambiguous,hot = Counter(),[],Counter()
    def label(row):
        site = sites.get((row['function'],row['pc']))
        if row['operation'] != 'Call' or site is None: return 'other'
        if row['kind'] == 'scalar_padding_clear':
            return 'padding_proven_empty' if site['padding_proven_empty'] else 'padding_unproved'
        if row['kind'] == 'entry_budget': return 'common_budget_at_scalar_site_upper_bound'
        return 'other'
    for root in parse_tree((folder/'sample.txt').read_text()):
        for count,frame,_ in self_samples(root):
            if '<unknown binary>' not in frame: continue
            offsets = [int(a,16)-mapping['arena_base'] for a in re.findall(r'0x([0-9a-f]+)',frame)]
            if not offsets or not any(0 <= p < len(code) for p in offsets):continue
            assert '...' not in frame and all(0 <= p < len(code) for p in offsets)
            coarse = [locate(checked,p) for p in offsets]
            assert len({(r['function'],r['region_pc'],r['pc'],r['kind']) for r in coarse}) == 1
            if coarse[0]['kind'] != 'transition':continue
            rows = [locate(fine,p) for p in offsets];labels = {label(r) for r in rows}
            if len(labels) != 1:ambiguous.append(dict(count=count,frame=frame));continue
            kind, = labels;counts[kind] += count
            if kind != 'other':hot[rows[0]['function'],rows[0]['pc'],kind] += count
    total = sum(counts.values())+sum(r['count'] for r in ambiguous)
    old = read(ROOT/case['report'])
    assert total == old['by_label']['transition:Call']+old['by_label']['transition:Return']
    return dict(name=case['name'],scalar_sites=len(sites),padding_proven_empty_sites=sum(r['padding_proven_empty'] for r in sites.values()),
        unique_callees=typed['unique_callees'],generated_samples=old['attributed_generated_samples'],transition_samples=total,
        samples=dict(counts),ambiguous=ambiguous,ambiguous_samples=sum(r['count'] for r in ambiguous),
        top_sites=[dict(**sites[fid,pc],part=kind,samples=count) for (fid,pc,kind),count in hot.most_common(20)],
        performance_measurement=False,entry_budget_samples_are_upper_bound=True)


def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);admission();frozen = {}
        def bind(p,expected=None):
            h = sha(p);assert expected is None or h == expected,p
            frozen[str(p.relative_to(ROOT))] = h
            return read(p) if p.suffix == '.json' else h
        folder = ROOT/'results/current-call-protocol-01'
        closed = bind(folder/'closure.json');assert closed['status'] == 'closed' and closed['all_hashes_verified']
        previous = bind(folder/'summary.json',closed['summary_sha256'])
        terminal = bind(folder/'terminal.json',closed['terminal_sha256']);assert terminal['returncode'] == 0
        assert previous['commands'] == 6 and previous['tests_per_profile'] == 3
        prior = bind(ROOT/previous['raw']/'plan.json',previous['plan_sha256'])
        records = bind(ROOT/previous['raw']/'records.json',previous['records_sha256'])
        for row in records:
            for p,h in row['outputs'].items(): bind(ROOT/p,h)
        for p,h in prior['frozen'].items():
            if p.startswith(('.work/','results/')):bind(ROOT/p,h)
        cases = []
        for i,case in enumerate(prior['cases']):
            report = bind(ROOT/case['report'])
            assert report['reconstructed_same_process_code'] and report['unassigned_generated_samples'] == 0
            for p,h in report['evidence'].items():bind(ROOT/p,h)
            sample_plan = bind((ROOT/case['folder']).parent/'plan.json')
            artifact = Path(sample_plan['artifact']);bind(artifact,sample_plan['artifact_sha256'])
            protocol = ROOT/previous['raw']/(str(i)+'-protocol.json');bind(protocol)
            cases.append(dict(case,index=i,artifact=str(artifact.relative_to(ROOT)),protocol=str(protocol.relative_to(ROOT))))
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
            target_purpose='typed scalar empty-work models and metadata only; no guest code execution',
            original_project_guest_commands=0,executable_code_publications=0,performance_measurement=False))
        env = {k:v for k,v in os.environ.items() if not k.startswith(('RUST_INTERP_','RUSTDEV_','CARGO_','PROTOCOL_','ENTRY_')) and k not in
            ['RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','RUSTC','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER','RUST_TEST_THREADS','PYTHONPATH']}
        assert not any(k.startswith('DYLD_') for k in env)
        env.update(CARGO_INCREMENTAL='0',CARGO_PROFILE_RELEASE_DEBUG='1',CARGO_PROFILE_DEV_DEBUG='0',
            CARGO_PROFILE_TEST_DEBUG='0',RUST_TEST_THREADS='2',CARGO_TERM_COLOR='never',PYTHONDONTWRITEBYTECODE='1')
        common = ['--locked','--offline','--jobs','2','--manifest-path',str(ROOT/'Cargo.toml'),'--target-dir',str(TARGET),'-p','rust-interp-bytecode','--lib']
        commands = [(label,['cargo','+nightly-2026-09-08','test',*extra,*common,'--','--exact','--test-threads=2',*NAMES],{})
            for label,extra in [('debug',[]),('release',['--release'])]]
        for case in cases:
            output = raw/(str(case['index'])+'-scope.json')
            commands.append((str(case['index']),['cargo','+nightly-2026-09-08','test','--release',*common,PREFIX+'observe_saved_scalar_entry_empty_work','--','--ignored','--exact','--test-threads=2'],
                dict(ENTRY_ARTIFACT=str(ROOT/case['artifact']),ENTRY_PROTOCOL=str(ROOT/case['protocol']),ENTRY_OUTPUT=str(output))))

        records,comparisons = [],[]
        for label,cmd,extra in commands:
            current = admission();require_space(ROOT,8)
            assert all(sha(ROOT/p) == h for p,h in frozen.items())
            usage,start = child_usage(),time.perf_counter()
            child,out,err = capture(cmd,cwd=ROOT,env=env|extra,receipt_path=raw/(label+'-child.json'),receipt=dict(label=label))
            elapsed,cpu = time.perf_counter()-start,child_cpu_since(usage)
            for stream,value in [('stdout',out),('stderr',err)]: (raw/(label+'.'+stream)).write_text(value)
            paths = [raw/(label+'-child.json')]
            if extra:paths.append(Path(extra['ENTRY_OUTPUT']))
            records.append(dict(label=label,command=cmd,extra_env=extra,pid=child.pid,returncode=child.returncode,
                seconds=elapsed,cpu=cpu,admission=current,stdout_sha256=sha(raw/(label+'.stdout')),stderr_sha256=sha(raw/(label+'.stderr')),
                outputs={str(p.relative_to(ROOT)):sha(p) for p in paths if p.is_file()}))
            write(raw/'records.json',records);assert child.returncode == 0,(out+err)[-6000:]
            if label in ['debug','release']:
                assert 'test result: ok. 2 passed; 0 failed; 0 ignored;' in out
                assert all(name+' ... ok' in out for name in NAMES)
            else:
                assert 'test result: ok. 1 passed; 0 failed; 0 ignored;' in out
                comparisons.append(derive(cases[int(label)],raw/(label+'-scope.json')))
                write(raw/'attribution.json',comparisons)
            records[-1]['after'] = admission();write(raw/'records.json',records)
            print(label,'typed scalar entry scope/controls passed',flush=True)
        assert all(sha(ROOT/p) == h for p,h in frozen.items())
        result = ROOT/'results'/RUN;result.mkdir(exist_ok=False)
        write(result/'summary.json',dict(status='passed',source_revision=revision,raw=str(raw.relative_to(ROOT)),
            plan_sha256=sha(raw/'plan.json'),records_sha256=sha(raw/'records.json'),commands=6,tests_per_profile=2,
            comparisons=comparisons,setup_seconds=sum(r['seconds'] for r in records),setup_cpu_seconds=sum(r['cpu']['total_seconds'] for r in records),
            original_project_guest_commands=0,executable_code_publications=0,performance_measurement=False))


def close():
    raw = ROOT/'.work'/RUN;terminal = read(ROOT/'.work/experiments'/RUN/'status.json')
    assert terminal['status'] == 'finished'
    if terminal['returncode'] == 0:
        plan,records,summary = read(raw/'plan.json'),read(raw/'records.json'),read(ROOT/'results'/RUN/'summary.json')
        assert summary['commands'] == len(records) == 6 and summary['tests_per_profile'] == 2
        assert [derive(c,raw/(str(c['index'])+'-scope.json')) for c in plan['cases']] == summary['comparisons']
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
                assert 'test result: ok. 2 passed; 0 failed; 0 ignored;' in out
    focus.RUN = RUN;focus.close()


if __name__ == '__main__':
    if sys.argv[1:] == ['--close']:close()
    else:
        assert len(sys.argv) == 1
        main()
