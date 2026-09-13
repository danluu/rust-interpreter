"""Join current same-process samples to native ranges and retained guest ops."""
from bisect import bisect_right
from collections import Counter
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from compare_saved_runtime import acquire_lock, sha
from summarize_owned_sample import parse_tree, self_samples
from workflow_io import require_space, write_json as write


def main():
    with (ROOT / '.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45)
        require_space(ROOT, 8)
        proof_path = ROOT / 'results/memory-operands-profile-01/summary.json'
        proof = json.loads(proof_path.read_text())
        assert proof['status'] == 'passed' and proof['exact_per_pc_counts']
        outputs = []
        for index, label in enumerate(['block', 'exhaustive']):
            run = 'current-runtime-sample-' + label + '-01'
            folder = ROOT / '.work' / run / '0'
            result = ROOT / 'results' / run
            summary_path = result / 'summary.json'
            summary = json.loads(summary_path.read_text())
            attribution_path = result / 'generated-attribution.json'
            attribution = json.loads(attribution_path.read_text())
            assert summary['vm_sha256'] == proof['vm_sha256'] == attribution['vm_sha256']
            record = json.loads((folder / 'record.json').read_text())
            assert all(sha(folder / p) == h for p, h in record['files'].items())
            native = json.loads((folder / 'jit-code/map.json').read_text())
            assert not native['profiled'] and native['pid'] == summary['samples'][0]['pid']
            profile_path = ROOT / proof['raw'] / f'{index}-profile.json'
            assert sha(profile_path) == proof['comparisons'][index]['profile_sha256']
            profile = json.loads(profile_path.read_text())
            ranges = native['ranges']
            offsets = [r['offset'] for r in ranges]
            assert offsets[0] == 0 and all(a['end'] == b['offset'] for a, b in zip(ranges, ranges[1:]))
            counts, unresolved = Counter(), 0
            for root in parse_tree((folder / 'sample.txt').read_text()):
                for count, frame, _ in self_samples(root):
                    if '<unknown binary>' not in frame:
                        continue
                    addresses = [int(a, 16) for a in re.findall(r'0x([0-9a-f]+)', frame)]
                    if '...' in frame or not addresses:
                        unresolved += count
                        continue
                    selected = set()
                    for address in addresses:
                        offset = address - native['arena_base']
                        assert 0 <= offset < native['code_bytes'] and offset % 4 == 0
                        selected.add(bisect_right(offsets, offset) - 1)
                    if len(selected) != 1:
                        unresolved += count
                        continue
                    counts[selected.pop()] += count
            assert sum(counts.values()) + unresolved == summary['disjoint_counts'].get('generated_code', 0) + summary['disjoint_counts'].get('unresolved_unknown_binary', 0)
            hot = []
            for which, samples in counts.most_common(10):
                region = ranges[which]
                function = profile['functions'][region['function']]
                assert function['name'] == region['name']
                lo, hi = region['pc'], region['pc_end']
                assert 0 <= lo < hi <= len(function['operations'])
                variants = Counter()
                for op in function['operations'][lo:hi]:
                    match = re.match(r'^([A-Z][A-Za-z0-9]*)(?: \{|$)', op)
                    assert match
                    variants[match[1]] += 1
                words = (region['end'] - region['offset']) // 4
                hot.append(dict(samples=samples, percent_of_window=100*samples/summary['total_samples'],
                    function=region['name'], kind=region['kind'], pc=lo, pc_end=hi,
                    emitted_words=words, guest_operations=hi-lo, words_per_guest_operation=words/(hi-lo),
                    guest_variant_counts=dict(variants)))
            outputs.append(dict(case=label, total_samples=summary['total_samples'],
                resolved_region_samples=sum(counts.values()), unresolved_region_samples=unresolved,
                hot_regions=hot, evidence={str(p.relative_to(ROOT)): sha(p) for p in
                    [proof_path, profile_path, summary_path, attribution_path, folder/'record.json',
                     folder/'jit-code/map.json', folder/'sample.txt']}))
        destination = ROOT / 'results/current-runtime-costs-01'
        destination.mkdir(exist_ok=False)
        write(destination / 'hot-regions.json', dict(status='passed', cases=outputs,
            script_sha256=sha(Path(__file__)), performance_measurement=False,
            limitation='Whole native regions include guards, wrappers, branches and tails. Static words/guest-op is not dynamic retired instructions or per-op host attribution. Rendered variants are descriptive only.'))


if __name__ == '__main__':
    main()
