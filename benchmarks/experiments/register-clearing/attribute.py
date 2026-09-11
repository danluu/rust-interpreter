#!/usr/bin/env python3
"""Split existing exact zeroing sequences by their typed Call's storage arena."""
from bisect import bisect_right
from collections import Counter
import json
from pathlib import Path
import re
import struct
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from attribute_generated_sample import ZERO_BULK, ZERO_RANGE, attribute, classify_words
from summarize_owned_sample import parse_tree, require, self_samples, sha


def zero_spans(data):
    """Match complete sequences once; the bulk tail is part of that same clear."""
    require(len(data) % 4 == 0, 'unaligned code')
    words = [word[0] for word in struct.iter_unpack('<I', data)]
    spans = []
    pc = 0
    while pc < len(words):
        pattern = next((p for p in (ZERO_BULK, ZERO_RANGE)
                        if tuple(words[pc:pc + len(p)]) == p), None)
        if pattern:
            spans.append((4 * pc, 4 * (pc + len(pattern)), pattern == ZERO_BULK))
            pc += len(pattern)
        else:
            pc += 1
    return spans


def call_spans(data, row, functions):
    caller = functions[row['function']]
    require(caller['id'] == row['function'] and caller['name'] == row['name'], 'caller identity differs')
    require(row['pc_end'] == row['pc'] + 1 <= caller['code_len'], 'call PC range differs')
    calls = [c for c in caller['calls'] if c['pc'] == row['pc']]
    require(len(calls) == 1, 'emitted call is not a typed direct Call')
    callee = functions[calls[0]['callee']]
    require(callee['id'] == calls[0]['callee'], 'callee identity differs')
    spans = zero_spans(data)
    sizes = [max(callee['frame_size'], 1)]
    arenas = ['guest_memory']
    if callee['needs_initial_zeroes']:
        sizes.append(callee['registers'] * 16)
        arenas.append('register_array')
    require(len(spans) == len(sizes), 'typed call/zero sequence count differs')
    require(all(bulk == (size >= 64) for (_, _, bulk), size in zip(spans, sizes)), 'zero loop size differs')
    return [(lo, hi, arena, callee['id']) for (lo, hi, _), arena in zip(spans, arenas)]


def analyze(run_id, artifact, metadata):
    work = ROOT / '.work' / run_id
    report_path = ROOT / 'results' / run_id / 'summary.json'
    original_path = report_path.with_name('generated-attribution.json')
    report = json.loads(report_path.read_text())
    original = json.loads(original_path.read_text())
    functions = json.loads(metadata.read_text())
    require(all(f['id'] == i for i, f in enumerate(functions)), 'nonsequential function IDs')
    counts, hot = Counter(), Counter()
    samples = []
    evidence = {str(p.relative_to(ROOT)): sha(p) for p in (report_path, original_path, artifact, metadata)}
    for sample in report['samples']:
        folder = work / str(sample['index'])
        # Retain every existing code/process/options/range/checksum validation.
        checked = attribute(folder, sample)
        require(checked == original['samples'][sample['index']], 'original attribution differs')
        record = json.loads((folder / 'record.json').read_text())
        require(Path(record['identity']['command'][-1]) == artifact, 'typed artifact differs from sampled command')
        dump = json.loads((folder / 'jit-code/map.json').read_text())
        data = (folder / 'jit-code/code.bin').read_bytes()
        require(dump['resumable_calls'] and dump['persistent_registers'], 'unexpected runtime configuration')
        spans = []
        for row in dump['ranges']:
            if row['kind'] == 'resumable_call':
                for lo, hi, arena, callee in call_spans(data[row['offset']:row['end']], row, functions):
                    spans.append((lo + row['offset'], hi + row['offset'], arena, callee))
        starts = [s[0] for s in spans]
        classes, _ = classify_words(data, resumable=True)
        exact = {i * 4 for i, kind in enumerate(classes) if kind in ('native_zero_range', 'native_zero_bulk')}
        require(exact == {pc for lo, hi, _, _ in spans for pc in range(lo, hi, 4)}, 'unattributed zeroing instructions')
        local = Counter()
        unresolved = []
        for root in parse_tree((folder / 'sample.txt').read_text()):
            for count, frame, _ in self_samples(root):
                if '<unknown binary>' not in frame:
                    continue
                addresses = [int(a, 16) for a in re.findall(r'0x([0-9a-f]+)', frame)]
                identities = []
                for address in addresses:
                    offset = address - dump['arena_base']
                    index = bisect_right(starts, offset) - 1
                    if index >= 0 and spans[index][0] <= offset < spans[index][1]:
                        identities.append(spans[index][2:])
                    else:
                        identities.append(('not_zeroing', None))
                if not identities or '...' in frame or len(set(identities)) != 1:
                    unresolved.append(dict(count=count, frame=frame))
                    continue
                arena, callee = identities[0]
                if arena != 'not_zeroing':
                    local[arena] += count
                    hot[(arena, callee)] += count
        require(not unresolved, 'ambiguous sample identities')
        require(sum(local.values()) == sum(checked['by_instruction_class'].get(k, 0)
                    for k in ('native_zero_range', 'native_zero_bulk')), 'zero samples do not reconcile')
        counts.update(local)
        samples.append(dict(index=sample['index'], pid=sample['pid'], counts=dict(local), unresolved=unresolved))
        for p in [folder / 'record.json', folder / 'sample.txt', folder / 'jit-code/map.json', folder / 'jit-code/code.bin']:
            evidence[str(p.relative_to(ROOT))] = sha(p)
    return dict(run_id=run_id, tool_key=report['tool_key'], vm_sha256=report['vm_sha256'],
        total_thread_samples=report['total_samples'], counts=dict(counts),
        percentages={k: 100 * v / report['total_samples'] for k, v in counts.items()}, samples=samples,
        hot_callees=[dict(arena=arena, samples=count, **{k: functions[callee][k] for k in
            ['id', 'name', 'frame_size', 'registers', 'needs_initial_zeroes']})
            for (arena, callee), count in hot.most_common()], evidence=evidence)
