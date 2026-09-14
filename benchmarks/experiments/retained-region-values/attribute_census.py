"""Attribute fresh saved scalar-runtime samples to reconstructed memory parts."""
from bisect import bisect_right
from collections import Counter
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from compare_saved_runtime import sha
from summarize_owned_sample import parse_tree, self_samples
from workflow_io import write_json as write


def locate(rows, starts, offset):
    i = bisect_right(starts, offset) - 1
    assert i >= 0 and rows[i]['offset'] <= offset < rows[i]['end'] and offset % 4 == 0
    return rows[i]


def identity(rows, offsets, starts=None):
    if starts is None:
        starts = [s['offset'] for s in rows]
    parts = [locate(rows, starts, o) for o in offsets]
    assert len({(s['function'], s['pc']) for s in parts}) == 1
    groups = {(s['part'], s['access']) for s in parts}
    return next(iter(groups)) if len(groups) == 1 else ('ambiguous', 'ambiguous')


def read(p):
    assert p.stat().st_size <= 256 * 1024**2
    return json.loads(p.read_text())


def main(run):
    proof_path = ROOT / 'results/scratch-memory-values-profile-01/summary.json'
    proof = read(proof_path)
    evidence = {str(proof_path.relative_to(ROOT)): sha(proof_path)}
    output = []
    for index, label in enumerate(['block', 'exhaustive']):
        folder = ROOT / '.work' / ('scratch-scalar-runtime-sample-' + label + '-01') / '0'
        report_path = ROOT / '.work' / run / (label + '.json')
        report = read(report_path)
        for k in ['complete_small_memory_partition', 'exact_full_function_reconstruction', 'observer_words_unchanged']:
            assert report[k] is True
        assert report['status'] == 'passed' and report['schema_version'] == 2 and report['scalar_bodies_reconstructed'] > 0
        assert report['guest_commands'] == report['executable_code_publications'] == 0
        map_path = folder / 'jit-code/operations.json'
        mapping = read(map_path)
        assert mapping['profiled'] is False and mapping['complete'] and mapping['reconstructed_bytes_match']
        assert report['code_sha256'] == mapping['code_sha256'] == sha(folder / 'jit-code/code.bin')
        old_path = ROOT / 'results' / ('scratch-scalar-runtime-sample-' + label + '-01') / 'operation-attribution.json'
        old = read(old_path)
        assert old['status'] == 'passed' and old['unassigned_generated_samples'] == 0
        assert all(sha(ROOT / p) == h for p, h in old['evidence'].items())
        comparison, = [r for r in proof['comparisons'] if r['mode'] == 'candidate' and r['index'] == index]
        profile_path = ROOT / comparison['profile_path']
        assert sha(profile_path) == comparison['profile_sha256']
        profile = read(profile_path)
        rows = [dict(s, function=f['function']) for f in report['functions'] for s in f['memory_spans']]
        starts = [s['offset'] for s in rows]
        assert starts == sorted(set(starts))
        coarse = [dict(s, function=f['function']) for f in mapping['functions'] for s in f['spans'] if s['offset'] < s['end']]
        coarse_starts = [s['offset'] for s in coarse]
        assert coarse_starts == sorted(set(coarse_starts))
        selected = {(f['function'], s['pc']): (s['operation'], s['size']) for f in report['functions'] for s in f['selected']}
        static, sampled, details, sites, copy_parts = [Counter() for _ in range(5)]
        for f in report['functions']:
            fid = f['function']
            assert profile['functions'][fid]['name'] == f['name']
            for s in f['memory_spans']:
                assert s['part'] != 'unclassified' and (s['operation'], s['size']) == selected[fid, s['pc']]
                assert profile['functions'][fid]['jit_block_ends'][s['region_start']] == s['region_end']
                owner = locate(coarse, coarse_starts, s['offset'])
                assert (owner['function'], owner['pc'], owner['kind']) == (fid, s['pc'], 'operation')
                assert s['offset'] < s['end'] <= owner['end']
                static[s['part']] += (s['end'] - s['offset']) // 4
        retained={};retained_static=Counter();retained_samples=Counter()
        for f in report['functions']:
            payload={s['pc'] for s in f['memory_spans'] if s['part'] in ['load_data','store_data']}
            for region in f['retained']:
                assert profile['functions'][f['function']]['jit_block_ends'][region['start']]==region['end']
                retained_static['work']+=region['work']
                plan=region['plan']
                if plan is None:retained_static['declined_regions']+=1;continue
                retained_static['analyzed_regions']+=1
                retained_static['selected_captures']+=len(plan['captures'])
                retained_static['selected_reuses']+=len(plan['uses'])
                for pc,use in plan['uses'].items():
                    pc=int(pc);origin=use['origin_pc'];capture=plan['captures'][str(origin)]
                    assert (use['size'],use['slot'])==(capture['size'],capture['slot'])
                    assert origin<pc and use['slot']<15
                    if origin in payload:
                        retained_static['materialized_origin_reuses']+=1
                        retained[f['function'],pc]=use
        generated = selected_samples = 0
        for root in parse_tree((folder / 'sample.txt').read_text()):
            for n, frame, _ in self_samples(root):
                if '<unknown binary>' not in frame:
                    continue
                assert '...' not in frame
                offsets = [int(a, 16) - mapping['arena_base'] for a in re.findall(r'0x([0-9a-f]+)', frame)]
                assert offsets
                owners = [locate(coarse, coarse_starts, o) for o in offsets]
                assert len({(s['function'], s['region_pc'], s['pc'], s['kind']) for s in owners}) == 1
                generated += n
                c = owners[0]
                key = (c['function'], c['pc'])
                if c['kind'] != 'operation' or key not in selected:
                    continue
                fine = [locate(rows, starts, o) for o in offsets]
                assert all((s['function'], s['pc']) == key for s in fine)
                part, access = identity(rows, offsets, starts)
                selected_samples += n
                sampled[part] += n
                operation, size = selected[key]
                details[f'{operation}/{size}:{access}:{part}'] += n
                sites[c['function'], c['pc'], operation, size, part, access] += n
                if key in retained and part=='load_data': retained_samples[f'{operation}/{size}']+=n
                if operation == 'Copy':
                    copy_parts[part] += n
        assert generated == old['attributed_generated_samples']
        expected = old['by_label'].get('operation:Load', 0) + old['by_label'].get('operation:Store', 0)
        expected += sum(n for d, n in old['by_detail'].items() if d.startswith('operation:Copy/') and int(d.split('/')[1]) <= 16)
        assert selected_samples == expected == sum(sampled.values())
        output.append(dict(case=label, ordinary_functions=len(report['functions']), scalar_bodies=report['scalar_bodies_reconstructed'],
            memory_part_spans=len(rows), static_words_by_part=dict(static), samples_by_part=dict(sampled),
            samples_by_detail=dict(details), copy_samples_by_part=dict(copy_parts), generated_samples=generated,
            selected_samples=selected_samples,retained_samples=dict(retained_samples),retained_static=dict(retained_static),top_sites=[dict(function=fid, name=profile['functions'][fid]['name'],
                pc=pc, operation=op, size=size, part=part, access=access, samples=n) for (fid, pc, op, size, part, access), n in sites.most_common(30)]))
        for p in [report_path, map_path, old_path, profile_path, folder / 'sample.txt', folder / 'jit-code/code.bin']:
            evidence[str(p.relative_to(ROOT))] = sha(p)
    out = ROOT / 'results' / run
    out.mkdir(exist_ok=True)
    details=ROOT/'.work'/run/'details.json'
    write(details,output)
    evidence[str(details.relative_to(ROOT))]=sha(details)
    for case in output:
        for key in ['top_sites','samples_by_detail']:case.pop(key)
    write(out / 'attribution.json', dict(status='passed', cases=output, evidence=evidence,
        guest_commands=0, performance_measurement=False, profile_used_for_static_identity_only=True,
        limitation='Profit-filtered typed complete-value retention model. Every guest write remains immediate; unknown writes invalidate origins. Native captures and temporary-register preservation are not implemented. Producer payload presence is necessary, not a full native lowering proof. Exact small-memory emitted subparts; partial perturbed normal-entropy self-PC samples. No dynamic profile counts, retired instructions, timing ratios or speedup inference.'))
    for case in output:
        print(json.dumps({k: case[k] for k in ['case', 'generated_samples', 'selected_samples', 'retained_samples', 'retained_static']}))


if __name__ == '__main__':
    main(sys.argv[1])
