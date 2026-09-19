"""Reclassify closed large ordinary clearing PCs; no build or guest execution."""
from collections import Counter
import hashlib
from pathlib import Path
import re
import subprocess
import sys
from large_clear_model import PATTERN, controls, matches, part

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'benchmarks/experiments/cross-program-template-model'))
import focus
from compare_saved_runtime import acquire_lock,sha
from workflow_io import require_space,write_json as write
from summarize_owned_sample import parse_tree,self_samples
sys.path.insert(0,str(ROOT/'benchmarks/experiments/scalar-private-transfers'))
from native_observation import validate,locate
read = focus.read
RUN = 'large-frame-clear-scope-01'
PRIOR = 'ordinary-padding-scope-02'


def derive(case, previous):
    assert case['name'] == previous['name'] and previous['ambiguous_samples'] == 0
    folder = ROOT/case['folder']
    protocol = read(ROOT/case['protocol'])
    code = (folder/'jit-code/code.bin').read_bytes()
    assert sha(folder/'jit-code/code.bin') == protocol['code_sha256']
    mapping,regions = read(folder/'jit-code/operations.json'),read(folder/'jit-code/map.json')
    checked = validate(mapping,regions,code,read(ROOT/case['profile']),read(folder/'record.json')['identity']['pid'])
    sites = {(r['caller'],r['pc']):dict(r) for r in previous['all_sites']}
    spans = {(r['function'],r['pc']):r for r in protocol['spans'] if r['kind'] == 'call_frame_clear'}
    assert len(sites) == len(previous['all_sites']) == len(spans) and set(sites) == set(spans)
    layouts,sizes = Counter(),Counter()
    for key,site in sites.items():
        span = spans[key]
        assert (site['offset'],site['end']) == (span['offset'],span['end'])
        found = matches(code[site['offset']:site['end']])
        large = site['callee_frame_size'] > 256
        assert len(found) == int(large),(key,site['callee_frame_size'],found)
        if not large: continue
        assert found == [site['end']-site['offset']-len(PATTERN)]
        site['helper_start'] = site['offset']+found[0]
        site['alignment_scope'] = 'bounded_alignment' if site['callee_frame_align'] <= 16 else 'large_alignment'
        site['padding_proven_empty'] = site['caller_frame_align'] >= site['callee_frame_align'] and max(site['caller_frame_size'],1)%site['callee_frame_align'] == 0
        layouts[site['alignment_scope']] += 1
        sizes[next((str(n) for n in [512,1024,2048,4096] if site['callee_frame_size'] <= n),'above4096')] += 1
    fine = dict(rows=protocol['spans'],starts=[r['offset'] for r in protocol['spans']])
    counts,proof_counts,hot,ambiguous = Counter(),Counter(),Counter(),[]
    clear_samples = transition_samples = 0
    for root in parse_tree((folder/'sample.txt').read_text()):
        for count,frame,_ in self_samples(root):
            if '<unknown binary>' not in frame: continue
            offsets = [int(a,16)-mapping['arena_base'] for a in re.findall(r'0x([0-9a-f]+)',frame)]
            if not offsets or not any(0 <= p < len(code) for p in offsets):continue
            assert '...' not in frame and all(0 <= p < len(code) and p%4 == 0 for p in offsets)
            coarse = [locate(checked,p) for p in offsets]
            assert len({(r['function'],r['region_pc'],r['pc'],r['kind']) for r in coarse}) == 1
            if coarse[0]['kind'] != 'transition':continue
            transition_samples += count
            rows = [locate(fine,p) for p in offsets]
            original = {(r['operation'],r['kind']) for r in rows}
            assert len(original) == 1
            if original != {('Call','call_frame_clear')}:continue
            clear_samples += count
            assert len({(r['function'],r['pc']) for r in rows}) == 1
            site = sites[rows[0]['function'],rows[0]['pc']]
            if site['callee_frame_size'] <= 256:
                counts['small_payload'] += count
                continue
            labels = {part(p-site['helper_start']) for p in offsets}
            if len(labels) != 1:
                ambiguous.append(dict(count=count,frame=frame,labels=sorted(labels)))
                continue
            label, = labels
            counts[site['alignment_scope']+'/'+label] += count
            proof_counts[('empty' if site['padding_proven_empty'] else 'dynamic')+'/'+label] += count
            hot[site['caller'],site['pc'],label] += count
    assert transition_samples == previous['transition_samples']
    assert clear_samples == previous['ordinary_clear_samples'] == case['expected_clear_samples']
    assert clear_samples == sum(counts.values())+sum(r['count'] for r in ambiguous)
    large_samples = clear_samples-counts['small_payload']
    assert large_samples == previous['samples'].get('large_payload/payload_or_setup',0)
    return dict(name=case['name'],generated_samples=previous['generated_samples'],transition_samples=transition_samples,
        ordinary_clear_samples=clear_samples,large_frame_samples=large_samples,static_large_sites=sum(layouts.values()),
        static_alignments=dict(layouts),static_size_buckets=dict(sizes),samples=dict(counts),padding_proof_samples=dict(proof_counts),
        ambiguous=ambiguous,ambiguous_samples=sum(r['count'] for r in ambiguous),
        top_sites=[dict(**sites[fid,pc],part=label,samples=count) for (fid,pc,label),count in hot.most_common(25)],
        performance_measurement=False,required_stores_are_not_removable_work=True)


def main():
    require_space(ROOT,12)
    model = controls()
    frozen = {}
    def bind(p,expected=None):
        h = sha(p);assert expected is None or h == expected,p
        frozen[str(p.relative_to(ROOT))] = h
        return read(p) if p.suffix == '.json' else h
    folder = ROOT/'results'/PRIOR
    closed = bind(folder/'closure.json');assert closed['status'] == 'closed' and closed['all_hashes_verified']
    previous = bind(folder/'summary.json',closed['summary_sha256'])
    terminal = bind(folder/'terminal.json',closed['terminal_sha256'])
    assert terminal['returncode'] == 0 and previous['status'] == 'passed'
    for key in ['evidence','source_bindings']:
        for p,h in bind(ROOT/closed[key],closed[key+'_sha256']).items():
            if key == 'evidence':bind(ROOT/p,h)
            else:
                data = subprocess.check_output(['git','show',h['revision']+':'+p],cwd=ROOT)
                assert hashlib.sha256(data).hexdigest() == h['sha256']
    prior_plan = bind(ROOT/previous['raw']/'plan.json',previous['plan_sha256'])
    assert len(prior_plan['cases']) == len(previous['comparisons']) == 4
    assert not subprocess.check_output(['git','diff','--name-only','24cd8e99','--','crates'],cwd=ROOT).strip()
    paths = [*HERE.glob('*.py'),*HERE.glob('*.md'),Path(focus.__file__),
        ROOT/'benchmarks/experiments/scalar-private-transfers/native_observation.py',
        ROOT/'crates/bytecode/src/jit/resumable.rs',ROOT/'crates/bytecode/src/jit/native_calls.rs']
    paths += [ROOT/'scripts'/p for p in ['compare_saved_runtime.py','workflow_io.py','supervise_experiment.py','summarize_owned_sample.py']]
    for p in paths:bind(p)
    assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=ROOT).strip()
    revision = subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    raw = ROOT/'.work'/RUN;raw.mkdir(exist_ok=False)
    write(raw/'records.json',[])
    write(raw/'plan.json',dict(owner=str(ROOT),source_revision=revision,frozen=frozen,cases=prior_plan['cases'],
        prior_summary=str((folder/'summary.json').relative_to(ROOT)),controls=model,
        controller_command=[sys.executable,*sys.orig_argv[1:]],expected_commands=0,
        minimum_free_gib=12,original_project_guest_commands=0,executable_code_publications=0,performance_measurement=False))
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,12)
        assert all(sha(ROOT/p) == h for p,h in frozen.items())
        comparisons = [derive(c,p) for c,p in zip(prior_plan['cases'],previous['comparisons'])]
        assert all(sha(ROOT/p) == h for p,h in frozen.items())
        out = ROOT/'results'/RUN;out.mkdir(exist_ok=False)
        write(out/'summary.json',dict(status='passed',source_revision=revision,raw=str(raw.relative_to(ROOT)),
            plan_sha256=sha(raw/'plan.json'),records_sha256=sha(raw/'records.json'),commands=0,controls=model,
            comparisons=comparisons,original_project_guest_commands=0,executable_code_publications=0,performance_measurement=False))
        print('Four saved large-frame sample partitions qualified; no children',flush=True)


def close():
    raw = ROOT/'.work'/RUN
    terminal = read(ROOT/'.work/experiments'/RUN/'status.json')
    assert terminal['status'] == 'finished'
    if terminal['returncode'] == 0:
        plan,summary = read(raw/'plan.json'),read(ROOT/'results'/RUN/'summary.json')
        assert summary['commands'] == 0 and read(raw/'records.json') == []
        assert summary['controls'] == plan['controls'] == controls()
        previous = read(ROOT/plan['prior_summary'])
        assert summary['comparisons'] == [derive(c,p) for c,p in zip(plan['cases'],previous['comparisons'])]
    focus.RUN = RUN;focus.close()


if __name__ == '__main__':
    if sys.argv[1:] == ['--close']:close()
    else:
        assert len(sys.argv) == 1
        main()
