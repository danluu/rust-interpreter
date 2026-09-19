"""Separate ordinary padding from payload clearing in exact closed captures."""
from collections import Counter
import os
from pathlib import Path
import re
import subprocess
import sys
import time
ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
from ordinary_padding_model import controls, matches, classify_layout
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
RUN = 'ordinary-padding-scope-01'
TEST = 'jit::code_spans::ordinary_padding_scope::observe_saved_ordinary_call_layouts'


def derive(case, path):
    typed = read(path)
    assert typed['status'] == 'passed'
    assert typed['artifact_sha256'] == sha(ROOT/case['artifact'])
    assert typed['protocol_sha256'] == sha(ROOT/case['protocol'])
    protocol = read(ROOT/case['protocol'])
    assert typed['code_sha256'] == protocol['code_sha256']
    assert typed['guest_commands'] == typed['executable_code_publications'] == 0
    sites = {(r['caller'], r['pc']): r for r in typed['sites']}
    assert len(sites) == len(typed['sites']) > 0
    expected = {(r['function'], r['pc']): r for r in protocol['spans'] if r['kind'] == 'call_frame_clear'}
    assert set(sites) == set(expected)
    folder = ROOT/case['folder']
    mapping, regions = read(folder/'jit-code/operations.json'), read(folder/'jit-code/map.json')
    code = (folder/'jit-code/code.bin').read_bytes()
    checked = validate(mapping, regions, code, read(ROOT/case['profile']), read(folder/'record.json')['identity']['pid'])
    assert sha(folder/'jit-code/code.bin') == typed['code_sha256']
    layouts, static_words = Counter(), Counter()
    for key, site in sites.items():
        span = expected[key]
        assert (site['offset'], site['end']) == (span['offset'], span['end'])
        assert 0 <= site['offset'] < site['end'] <= len(code)
        assert site['offset'] % 4 == site['end'] % 4 == 0
        layout = classify_layout(site)
        offsets = matches(code[site['offset']:site['end']])
        dynamic = layout in ['bounded_padding', 'large_alignment_padding']
        assert len(offsets) == int(dynamic), (key, layout, offsets)
        site['layout'] = layout
        site['padding_offset'] = site['offset'] + offsets[0] if dynamic else None
        if dynamic:
            # clear_call_frame starts with this prefix; any future setup change
            # requires an explicit matcher update, never an inferred match.
            assert offsets == [0]
        layouts[layout] += 1
        static_words[layout] += (site['end'] - site['offset'])//4
    fine = dict(rows=protocol['spans'], starts=[r['offset'] for r in protocol['spans']])
    counts, ambiguous, hot = Counter(), [], Counter()
    clear_samples = transition_samples = 0
    def label(row, offset):
        if row['kind'] != 'call_frame_clear': return 'other'
        site = sites[row['function'], row['pc']]
        start = site['padding_offset']
        part = 'payload_or_setup'
        if start is not None:
            position = offset - start
            if 0 <= position < 12: part = 'padding_setup'
            elif 12 <= position < 36: part = 'padding_chunks'
            elif 36 <= position < 52: part = 'padding_bytes'
        return site['layout'] + '/' + part
    for root in parse_tree((folder/'sample.txt').read_text()):
        for count, frame, _ in self_samples(root):
            if '<unknown binary>' not in frame: continue
            offsets = [int(a,16)-mapping['arena_base'] for a in re.findall(r'0x([0-9a-f]+)',frame)]
            if not offsets or not any(0 <= p < len(code) for p in offsets): continue
            assert '...' not in frame and all(0 <= p < len(code) for p in offsets)
            coarse = [locate(checked,p) for p in offsets]
            assert len({(r['function'],r['region_pc'],r['pc'],r['kind']) for r in coarse}) == 1
            if coarse[0]['kind'] != 'transition': continue
            transition_samples += count
            rows = [locate(fine,p) for p in offsets]
            original = {(r['operation'],r['kind']) for r in rows}
            # The closed original protocol report has zero ambiguity. Verify it.
            assert len(original) == 1
            if original != {('Call','call_frame_clear')}: continue
            clear_samples += count
            labels = {label(r,p) for r,p in zip(rows,offsets)}
            if len(labels) != 1:
                ambiguous.append(dict(count=count,frame=frame,labels=sorted(labels)))
                continue
            kind, = labels
            counts[kind] += count
            assert len({(r['function'],r['pc']) for r in rows}) == 1
            hot[rows[0]['function'],rows[0]['pc'],kind] += count
    old = read(ROOT/case['report'])
    assert transition_samples == old['by_label']['transition:Call']+old['by_label']['transition:Return']
    assert clear_samples == case['expected_clear_samples']
    assert clear_samples == sum(counts.values()) + sum(r['count'] for r in ambiguous)
    return dict(name=case['name'],ordinary_sites=len(sites),static_layouts=dict(layouts),static_words=dict(static_words),
        generated_samples=old['attributed_generated_samples'],transition_samples=transition_samples,
        ordinary_clear_samples=clear_samples,samples=dict(counts),ambiguous=ambiguous,
        ambiguous_samples=sum(r['count'] for r in ambiguous),
        top_sites=[dict(**sites[fid,pc],part=kind,samples=count) for (fid,pc,kind),count in hot.most_common(30)],
        all_sites=list(sites.values()),performance_measurement=False,
        padding_setup_includes_necessary_empty_case_work=True)


def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);admission();model_controls = controls();frozen = {}
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
            assert previous['comparisons'][i]['name'] == case['name']
            cases.append(dict(case,index=i,artifact=str(artifact.relative_to(ROOT)),protocol=str(protocol.relative_to(ROOT)),
                expected_clear_samples=previous['comparisons'][i]['fine_samples']['Call/call_frame_clear']))
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
            controller_command=[sys.executable,*sys.orig_argv[1:]],expected_commands=4,controls=model_controls,target=str(TARGET),
            target_purpose='typed ordinary-call layouts and padding scope only; no guest code execution',
            original_project_guest_commands=0,executable_code_publications=0,performance_measurement=False))
        env = {k:v for k,v in os.environ.items() if not k.startswith(('RUST_INTERP_','RUSTDEV_','CARGO_','PROTOCOL_','ENTRY_','PADDING_')) and k not in
            ['RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','RUSTC','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER','RUST_TEST_THREADS','PYTHONPATH']}
        assert not any(k.startswith('DYLD_') for k in env)
        env.update(CARGO_INCREMENTAL='0',CARGO_PROFILE_RELEASE_DEBUG='1',CARGO_PROFILE_DEV_DEBUG='0',
            CARGO_PROFILE_TEST_DEBUG='0',RUST_TEST_THREADS='2',CARGO_TERM_COLOR='never',PYTHONDONTWRITEBYTECODE='1')
        common = ['--locked','--offline','--jobs','2','--manifest-path',str(ROOT/'Cargo.toml'),'--target-dir',str(TARGET),'-p','rust-interp-bytecode','--lib']
        commands = []
        for case in cases:
            output = raw/(str(case['index'])+'-scope.json')
            commands.append((str(case['index']),['cargo','+nightly-2026-09-08','test','--release',*common,TEST,'--','--ignored','--exact','--test-threads=2'],
                dict(PADDING_ARTIFACT=str(ROOT/case['artifact']),PADDING_PROTOCOL=str(ROOT/case['protocol']),PADDING_OUTPUT=str(output))))

        records,comparisons = [],[]
        for label,cmd,extra in commands:
            current = admission();require_space(ROOT,8)
            assert all(sha(ROOT/p) == h for p,h in frozen.items())
            usage,start = child_usage(),time.perf_counter()
            child,out,err = capture(cmd,cwd=ROOT,env=env|extra,receipt_path=raw/(label+'-child.json'),receipt=dict(label=label))
            elapsed,cpu = time.perf_counter()-start,child_cpu_since(usage)
            for stream,value in [('stdout',out),('stderr',err)]: (raw/(label+'.'+stream)).write_text(value)
            paths = [raw/(label+'-child.json')]
            if extra:paths.append(Path(extra['PADDING_OUTPUT']))
            records.append(dict(label=label,command=cmd,extra_env=extra,pid=child.pid,returncode=child.returncode,
                seconds=elapsed,cpu=cpu,admission=current,stdout_sha256=sha(raw/(label+'.stdout')),stderr_sha256=sha(raw/(label+'.stderr')),
                outputs={str(p.relative_to(ROOT)):sha(p) for p in paths if p.is_file()}))
            write(raw/'records.json',records);assert child.returncode == 0,(out+err)[-6000:]
            assert 'test result: ok. 1 passed; 0 failed; 0 ignored;' in out
            assert TEST+' ... ok' in out
            comparisons.append(derive(cases[int(label)],raw/(label+'-scope.json')))
            write(raw/'attribution.json',comparisons)
            records[-1]['after'] = admission();write(raw/'records.json',records)
            print(label,'ordinary padding metadata and attribution passed',flush=True)
        assert all(sha(ROOT/p) == h for p,h in frozen.items())
        result = ROOT/'results'/RUN;result.mkdir(exist_ok=False)
        write(result/'summary.json',dict(status='passed',source_revision=revision,raw=str(raw.relative_to(ROOT)),
            plan_sha256=sha(raw/'plan.json'),records_sha256=sha(raw/'records.json'),commands=4,controls=model_controls,
            outputs={str((raw/'attribution.json').relative_to(ROOT)):sha(raw/'attribution.json')},
            comparisons=comparisons,setup_seconds=sum(r['seconds'] for r in records),setup_cpu_seconds=sum(r['cpu']['total_seconds'] for r in records),
            original_project_guest_commands=0,executable_code_publications=0,performance_measurement=False))


def close():
    raw = ROOT/'.work'/RUN;terminal = read(ROOT/'.work/experiments'/RUN/'status.json')
    assert terminal['status'] == 'finished'
    if terminal['returncode'] == 0:
        plan,records,summary = read(raw/'plan.json'),read(raw/'records.json'),read(ROOT/'results'/RUN/'summary.json')
        assert summary['commands'] == len(records) == 4
        assert summary['controls'] == plan['controls'] == controls()
        assert [derive(c,raw/(str(c['index'])+'-scope.json')) for c in plan['cases']] == summary['comparisons']
        for r in records:
            for receipt in [r['admission'],r['after']]:
                assert receipt['allocated_target_bytes'] <= 3*1024**3
                assert receipt['required_free_bytes'] == max(14*1024**3,8*1024**3+2*receipt['allocated_target_bytes'])
                assert receipt['free_bytes'] >= receipt['required_free_bytes']
            child = read(raw/(r['label']+'-child.json'))
            assert child['status'] == 'finished' and child['returncode'] == r['returncode'] == 0
            assert child['pid'] == r['pid'] and child['parent_pid'] == terminal['child_pid'] and child['command'] == r['command']
            out = (raw/(r['label']+'.stdout')).read_text()
            assert TEST+' ... ok' in out
            assert 'test result: ok. 1 passed; 0 failed; 0 ignored;' in out
        assert summary['comparisons'] == read(raw/'attribution.json')
        assert summary['setup_seconds'] == sum(r['seconds'] for r in records)
        assert summary['setup_cpu_seconds'] == sum(r['cpu']['total_seconds'] for r in records)
    focus.RUN = RUN;focus.close()


if __name__ == '__main__':
    if sys.argv[1:] == ['--close']:close()
    else:
        assert len(sys.argv) == 1
        main()
