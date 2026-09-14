"""Refine previously assigned transition self-PCs; do not collect new samples."""
from bisect import bisect_right
from collections import Counter
from pathlib import Path
import argparse
import json
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    assert re.fullmatch(r'scalar-protocol-census-\d{2}', args.run_id)
    work = ROOT / '.work' / args.run_id
    output = []
    for label in ['block', 'exhaustive']:
        folder = ROOT / '.work' / ('scratch-scalar-runtime-sample-' + label + '-01') / '0'
        old_path = ROOT / 'results' / ('scratch-scalar-runtime-sample-' + label + '-01') / 'operation-attribution.json'
        old = json.loads(old_path.read_text())
        assert old['status'] == 'passed' and old['unassigned_generated_samples'] == 0
        assert all(sha(ROOT / p) == h for p, h in old['evidence'].items())
        expected = old['by_label']['transition:Call'] + old['by_label']['transition:Return']
        mapping = json.loads((folder / 'jit-code/operations.json').read_text())
        report_path = work / (label + '.json')
        report = json.loads(report_path.read_text())
        assert report['status'] == 'passed' and report['exact_full_function_reconstruction']
        assert report['exact_transition_reconstruction'] and report['complete_partition']
        assert report['schema_version']==2 and report['scalar_bodies_reconstructed']>0
        assert report['code_sha256'] == mapping['code_sha256'] == sha(folder / 'jit-code/code.bin')
        assert report['guest_commands'] == report['executable_code_publications'] == 0
        spans = report['spans']; starts = [s['offset'] for s in spans]
        assert starts == sorted(set(starts))
        rows = [dict(s, function=f['function']) for f in mapping['functions'] for s in f['spans'] if s['offset'] < s['end']]
        coarse_starts = [s['offset'] for s in rows]
        assert coarse_starts == sorted(set(coarse_starts))
        transitions = [r for r in rows if r['kind'] == 'transition']
        assert len(transitions) == report['transitions']
        next_span = 0
        for row in transitions:
            cursor = row['offset']
            while next_span < len(spans) and spans[next_span]['offset'] < row['end']:
                span = spans[next_span]
                assert span['offset'] == cursor < span['end'] <= row['end']
                assert (span['function'], span['pc']) == (row['function'], row['pc'])
                cursor = span['end']; next_span += 1
            assert cursor == row['end']
        assert next_span == len(spans)
        counts, sites, unresolved = Counter(), Counter(), []
        coarse_counts = Counter()
        frames = [f for root in parse_tree((folder / 'sample.txt').read_text()) for f in self_samples(root)]
        for count, frame, _ in frames:
            if '<unknown binary>' not in frame: continue
            assert '...' not in frame
            addresses = [int(a, 16) - mapping['arena_base'] for a in re.findall(r'0x([0-9a-f]+)', frame)]
            assert addresses
            coarse = [locate(rows, coarse_starts, a) for a in addresses]
            assert len({(r['function'], r['region_pc'], r['pc'], r['kind']) for r in coarse}) == 1
            if coarse[0]['kind'] != 'transition': continue
            fine = [locate(spans, starts, a) for a in addresses]
            identities = {(r['operation'], r['kind'], r['argument']) for r in fine}
            operations = {r['operation'] for r in fine}; assert len(operations) == 1
            coarse_counts[next(iter(operations))] += count
            if len(identities) != 1:
                unresolved.append(dict(count=count, reason='multiple_protocol_labels', frame=frame)); continue
            operation, kind, argument = next(iter(identities))
            counts[operation + '/' + kind] += count
            sites[(coarse[0]['function'], coarse[0]['pc'], operation, kind, argument)] += count
        assert sum(counts.values()) + sum(r['count'] for r in unresolved) == expected
        assert coarse_counts == {op: old['by_label']['transition:' + op] for op in ['Call', 'Return']}
        static = Counter()
        for s in spans: static[s['operation'] + '/' + s['kind']] += (s['end'] - s['offset']) // 4
        names = {f['function']: f['name'] for f in mapping['functions']}
        output.append(dict(case=label, generated_samples=old['attributed_generated_samples'], transition_samples=expected,
            coarse_counts=dict(coarse_counts), fine_samples=dict(counts.most_common()),
            unassigned_fine_samples=sum(r['count'] for r in unresolved), unresolved=unresolved,
            static_words=dict(static), functions=report['functions'], transitions=report['transitions'],
            labels=len(spans), scalar_bodies=report['scalar_bodies_reconstructed'], top_sites=[dict(function=f, name=names[f], pc=pc, operation=op, kind=k, argument=a, samples=n)
                for (f, pc, op, k, a), n in sites.most_common(30)],
            evidence={str(p.relative_to(ROOT)): sha(p) for p in [old_path, report_path, folder / 'sample.txt',
                folder / 'jit-code/operations.json', folder / 'jit-code/code.bin']}))
    result = ROOT / 'results' / args.run_id; result.mkdir(exist_ok=True)
    write(result / 'attribution.json', dict(status='passed', cases=output, guest_commands=0,
        performance_measurement=False, limitation='One partial perturbed captured window per case; reuse of existing PCs only. Static words include unexecuted paths and are not retired instructions. No speedup claim.'))
    for case in output: print(json.dumps({k: case[k] for k in ['case', 'transition_samples', 'fine_samples', 'unassigned_fine_samples']}))


if __name__ == '__main__': main()
