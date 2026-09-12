#!/usr/bin/env python3
"""Split exact sampled cursor loads/stores by the qualified cursor layout."""
import argparse
from bisect import bisect_right
from collections import Counter
import json
from pathlib import Path
import re
import struct
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from attribute_generated_sample import attribute
from summarize_owned_sample import parse_tree, require, self_samples, sha

FIELDS = dict(enumerate(['remaining', 'profile_hits', 'memory_len', 'peak_linear',
    'register_len', 'frame_len', 'calls', 'returns', 'frames', 'registers', 'entries',
    'profiles', 'memory_end', 'register_end', 'frame_end', 'frame_limit', 'working_budget']))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--source', type=Path, default=ROOT / '.work/fixed-frame-clear-combined-build-01/source',
                        help='source whose cursor files match the frozen sample manifest')
    args = parser.parse_args()
    run = args.run_id
    require(Path(run).name == run and run not in ['.', '..'], 'invalid run ID')
    work = ROOT / '.work' / run
    source = args.source.resolve()
    paths = ['crates/bytecode/src/native_continuation.rs', 'crates/bytecode/src/jit/resumable.rs']
    plan = json.loads((work / 'plan.json').read_text())
    require(all(sha(source / p) == plan['source_files'][p] for p in paths), 'sampled cursor source differs')
    # Bind the decoder's byte offsets to the compile-time assertions in the
    # tested source snapshot, rather than to a later editable checkout.
    state = (source / paths[0]).read_text()
    cursor = (source / paths[1]).read_text()
    require('REMAINING == 0 && PROFILE_HITS == 8 && MEMORY_LEN == 16 && PEAK_LINEAR == 24' in state and
        'REGISTER_LEN == 32 && FRAME_LEN == 40 && CALLS == 48 && RETURNS == 56' in state and
        'FRAMES == 64 && REGISTERS == 72 && ENTRIES == 80 && PROFILES == 88' in cursor and
        'MEMORY_END == 96 && REGISTER_END == 104 && FRAME_END == 112' in cursor and
        'FRAME_LIMIT == 120 && WORKING_BUDGET == 128' in cursor, 'cursor layout assertions differ')
    report_path = ROOT / 'results' / run / 'summary.json'
    report = json.loads(report_path.read_text())
    totals, details, samples = Counter(), Counter(), []
    for sample in report['samples']:
        folder = work / str(sample['index'])
        checked = attribute(folder, sample)
        dump = json.loads((folder / 'jit-code/map.json').read_text())
        require(dump['resumable_calls'], 'expected resumable cursor ABI')
        words = [w[0] for w in struct.iter_unpack('<I', (folder / 'jit-code/code.bin').read_bytes())]
        ranges = dump['ranges']
        starts = [r['offset'] for r in ranges]
        local = Counter()
        for tree in parse_tree((folder / 'sample.txt').read_text()):
            for count, frame, _ in self_samples(tree):
                if '<unknown binary>' not in frame:
                    continue
                identities = []
                for address in re.findall(r'0x([0-9a-f]+)', frame):
                    offset = int(address, 16) - dump['arena_base']
                    word = words[offset // 4]
                    operation = {0xf9400260: 'load', 0xf9000260: 'store'}.get(word & 0xffc003e0)
                    if operation is None:
                        identities.append(None)
                    else:
                        slot = (word >> 10) & 0xfff
                        require(slot in FIELDS, 'unknown cursor field')
                        row = ranges[bisect_right(starts, offset) - 1]
                        identities.append((FIELDS[slot], operation, row['kind']))
                require(identities and '...' not in frame and len(set(identities)) == 1, 'ambiguous sampled cursor PC')
                if identities[0] is not None:
                    field, operation, kind = identities[0]
                    local[field] += count
                    details[(field, operation, kind)] += count
        require(sum(local.values()) == checked['by_instruction_class'].get('cursor_load_store', 0),
            'cursor samples do not reconcile with original code attribution')
        totals.update(local)
        samples.append(dict(index=sample['index'], pid=sample['pid'], fields=dict(local)))
    result = dict(status='passed', total_thread_samples=report['total_samples'], cursor_samples=sum(totals.values()),
        fields=[dict(field=f, samples=n, percent=100 * n / report['total_samples']) for f, n in totals.most_common()],
        details=[dict(field=f, operation=o, entry_kind=k, samples=n) for (f, o, k), n in details.most_common()],
        samples=samples, performance_measurement=False,
        evidence={str(p.resolve().relative_to(ROOT)): sha(p) for p in [Path(__file__), report_path, work / 'plan.json',
            *(source / p for p in paths)]},
        limitation='Partial perturbed windows. A load/store sample is not a standalone cost or a prediction of savings from removing it.')
    output = report_path.with_name('cursor-attribution.json')
    with output.open('x') as f:
        json.dump(result, f, indent=2)
        f.write('\n')
    print(json.dumps(dict(cursor_samples=result['cursor_samples'], fields=result['fields'])))


if __name__ == '__main__':
    main()
