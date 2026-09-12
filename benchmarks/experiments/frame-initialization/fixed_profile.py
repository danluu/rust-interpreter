#!/usr/bin/env python3
"""Attribute fixed and loop clearing in a new, exactly bound es8 code sample."""
import argparse
from bisect import bisect_right
from collections import Counter
import importlib.util
import json
from pathlib import Path
import re
import struct
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from attribute_generated_sample import attribute, classify_words
from summarize_owned_sample import parse_tree, require, self_samples, sha

spec = importlib.util.spec_from_file_location('loop_clearing', ROOT / 'benchmarks/experiments/register-clearing/attribute.py')
loops = importlib.util.module_from_spec(spec)
spec.loader.exec_module(loops)

# The fixed guest-frame clear is bounded by these two existing instructions:
# add x12,x2,x3 (end pointer), then ldr x9,[x19,#24] (peak guest-memory count).
END_POINTER = 0x8b03004c
LOAD_PEAK = 0xf9400e69


def zero_store(word):
    """Decode only non-writeback zero stores based on x11; return byte range."""
    if word & ~(0x7f << 15) == 0xa9007d7f:
        offset = (word >> 15) & 0x7f
        return ((offset if offset < 64 else offset - 128) * 8, 16)
    for opcode, width in [(0xf9000000, 8), (0xb9000000, 4), (0x79000000, 2), (0x39000000, 1)]:
        if word & ~(0xfff << 10) == opcode | (11 << 5) | 31:
            return (((word >> 10) & 0xfff) * width, width)
    return None


def fixed_span(data, size):
    require(0 < size <= 256 and len(data) % 4 == 0, 'invalid fixed clear extent')
    words = [w[0] for w in struct.iter_unpack('<I', data)]
    candidates = []
    for index, word in enumerate(words):
        if word != END_POINTER:
            continue
        end, covered = index + 1, 0
        while end < len(words) and end - index <= 20:
            store = zero_store(words[end])
            if store is None or store[0] != covered:
                break
            covered += store[1]
            end += 1
        if end < len(words) and words[end] == LOAD_PEAK and covered == size:
            candidates.append((4 * (index + 1), 4 * end))
    require(len(candidates) == 1, 'typed fixed clear has no unique exact contiguous store sequence')
    return candidates[0]


def call_spans(data, row, functions):
    caller = functions[row['function']]
    require(caller['id'] == row['function'] and caller['name'] == row['name'], 'caller identity differs')
    require(row['pc_end'] == row['pc'] + 1 <= caller['code_len'], 'Call PC differs')
    calls = [c for c in caller['calls'] if c['pc'] == row['pc']]
    require(len(calls) == 1, 'range is not one typed direct Call')
    callee = functions[calls[0]['callee']]
    require(callee['id'] == calls[0]['callee'], 'callee identity differs')
    align = callee['frame_align']
    require(align > 0 and align & (align - 1) == 0, 'invalid callee alignment')
    end = max(caller['frame_size'], 1)
    extent = (-end % align) + max(callee['frame_size'], 1)
    fixed = caller['frame_align'] >= align and extent <= 256
    spans = loops.zero_spans(data)
    sizes, arenas = [], []
    result = []
    if fixed:
        lo, hi = fixed_span(data, extent)
        result.append((lo, hi, 'guest_memory', 'fixed', callee['id']))
    else:
        sizes.append(max(callee['frame_size'], 1))
        arenas.append('guest_memory')
    if callee['needs_initial_zeroes']:
        sizes.append(callee['registers'] * 16)
        arenas.append('register_array')
    require(len(spans) == len(sizes), 'typed loop-clear count differs')
    require(all(bulk == (size >= 64) for (_, _, bulk), size in zip(spans, sizes)), 'typed loop size differs')
    result += [(lo, hi, arena, 'loop', callee['id']) for (lo, hi, _), arena in zip(spans, arenas)]
    result.sort()
    require(all(a[1] <= b[0] for a, b in zip(result, result[1:])), 'overlapping clear attribution')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    run = parser.parse_args().run_id
    require(Path(run).name == run and run not in ['.', '..'], 'invalid run ID')
    work = ROOT / '.work' / run
    report_path = ROOT / 'results' / run / 'summary.json'
    report = json.loads(report_path.read_text())
    artifact = ROOT / '.work/fre-integration-es8-edit-01/artifacts/restored.rbc'
    proof = ROOT / '.work/frame-initialization-proof-01'
    proof_summary = json.loads((proof / 'summary.json').read_text())
    require(proof_summary['status'] == 'passed', 'typed proof metadata not qualified')
    require(all(sha(ROOT / p) == h for p, h in proof_summary['evidence'].items()), 'typed evidence changed')
    proof_plan = json.loads((proof / 'plan.json').read_text())
    require(sha(artifact) == proof_plan['frozen'][str(artifact.relative_to(ROOT))], 'typed artifact changed')
    functions = json.loads((proof / 'es8-proof.stdout').read_text())
    require(all(f['id'] == i for i, f in enumerate(functions)), 'function indices differ')
    totals, classes, hot, samples = Counter(), Counter(), Counter(), []
    for sample in report['samples']:
        folder = work / str(sample['index'])
        checked = attribute(folder, sample)
        record = json.loads((folder / 'record.json').read_text())
        require(Path(record['identity']['command'][-1]) == artifact, 'sampled a different artifact')
        dump = json.loads((folder / 'jit-code/map.json').read_text())
        require(dump['resumable_calls'] and dump['persistent_registers'], 'different runtime options')
        data = (folder / 'jit-code/code.bin').read_bytes()
        spans = []
        for row in dump['ranges']:
            if row['kind'] == 'resumable_call':
                spans += [(lo + row['offset'], hi + row['offset'], arena, kind, callee)
                    for lo, hi, arena, kind, callee in call_spans(data[row['offset']:row['end']], row, functions)]
        starts = [s[0] for s in spans]
        classified, _ = classify_words(data, resumable=True)
        loop_pcs = {i * 4 for i, kind in enumerate(classified) if kind in ['native_zero_range', 'native_zero_bulk']}
        require(loop_pcs == {pc for lo, hi, _, kind, _ in spans if kind == 'loop' for pc in range(lo, hi, 4)},
            'unattributed loop-clearing instructions')
        require(all(classified[pc // 4] == 'other_generated' for lo, hi, _, kind, _ in spans
            if kind == 'fixed' for pc in range(lo, hi, 4)), 'fixed stores overlap another instruction class')
        counts = Counter()
        for root in parse_tree((folder / 'sample.txt').read_text()):
            for count, frame, _ in self_samples(root):
                if '<unknown binary>' not in frame:
                    continue
                identities = []
                for address in re.findall(r'0x([0-9a-f]+)', frame):
                    offset = int(address, 16) - dump['arena_base']
                    index = bisect_right(starts, offset) - 1
                    identities.append(spans[index][2:] if index >= 0 and spans[index][0] <= offset < spans[index][1] else None)
                require(identities and len(set(identities)) == 1 and '...' not in frame, 'ambiguous sample identity')
                if identities[0] is not None:
                    arena, kind, callee = identities[0]
                    counts[arena + '_' + kind] += count
                    hot[(arena, kind, callee)] += count
        old_classes = Counter(checked['by_instruction_class'])
        require(sum(v for k, v in counts.items() if k.endswith('_loop')) ==
            old_classes['native_zero_range'] + old_classes['native_zero_bulk'], 'loop sample totals differ')
        fixed = counts['guest_memory_fixed']
        old_classes['other_generated'] -= fixed
        old_classes['native_zero_fixed'] = fixed
        require(old_classes['other_generated'] >= 0 and sum(old_classes.values()) == checked['generated_samples'],
            'instruction classes do not reconcile')
        classes.update(old_classes)
        totals.update(counts)
        samples.append(dict(index=sample['index'], pid=sample['pid'], counts=dict(counts),
            by_instruction_class=dict(old_classes), typed_clear_sites=len(spans)))
    result = dict(status='passed', performance_measurement=False, tool_key=report['tool_key'],
        vm_sha256=report['vm_sha256'], total_thread_samples=report['total_samples'], counts=dict(totals),
        by_instruction_class=dict(classes), percentages={k: 100 * v / report['total_samples'] for k, v in classes.items()},
        samples=samples, hot_callees=[dict(arena=arena, kind=kind, samples=n, callee=callee,
            name=functions[callee]['name']) for (arena, kind, callee), n in hot.most_common()],
        evidence={str(p.relative_to(ROOT)): sha(p) for p in [Path(__file__), Path(loops.__file__),
            report_path, artifact, proof / 'summary.json', proof / 'plan.json', proof / 'es8-proof.stdout']},
        limitation='Partial perturbed sample windows. Typed call and exact emitted-byte attribution; no speedup prediction or latency comparison.')
    output = report_path.with_name('fixed-clearing-attribution.json')
    with output.open('x') as f:
        json.dump(result, f, indent=2)
        f.write('\n')
    print(json.dumps({k: result[k] for k in ['counts', 'percentages', 'total_thread_samples']}))


if __name__ == '__main__':
    main()
