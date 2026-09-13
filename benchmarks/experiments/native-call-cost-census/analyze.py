"""Join typed direct targets to existing sampled native protocol PCs."""
from bisect import bisect_right
from collections import Counter, defaultdict
import re


def variant(text):
    match = re.match(r'^([A-Z][A-Za-z0-9]*)(?: \{|$)', text)
    assert match, text[:80]
    return match[1]


def call_index(report, profile):
    calls = {}
    seen = set()
    for f in report['functions']:
        fid = f['function']
        assert fid not in seen
        seen.add(fid)
        pf = profile['functions'][fid]
        assert f['name'] == pf['name']
        for call in f['calls']:
            pc, callee = call['pc'], call['callee']
            assert 0 <= callee < len(profile['functions'])
            assert 0 <= pc < len(pf['operations'])
            assert variant(pf['operations'][pc]) == 'Call'
            assert pf['jit_block_ends'][pc] == pc + 1
            key = (fid, pc)
            assert key not in calls
            calls[key] = dict(callee=callee, hits=pf['jit_blocks'][pc])
    for fid, pf in enumerate(profile['functions']):
        for pc, hits in enumerate(pf['jit_blocks']):
            if hits and variant(pf['operations'][pc]) == 'Call':
                assert (fid, pc) in calls, (fid, pc)
    return calls


def locate(rows, starts, offset):
    index = bisect_right(starts, offset) - 1
    assert index >= 0 and offset % 4 == 0
    assert rows[index]['offset'] <= offset < rows[index]['end']
    return rows[index]


def attribute(calls, mapping, fine, samples):
    coarse = [dict(s, function=f['function']) for f in mapping['functions']
              for s in f['spans'] if s['offset'] < s['end']]
    starts = [s['offset'] for s in coarse]
    parts = fine['spans']
    part_starts = [s['offset'] for s in parts]
    assert starts == sorted(set(starts)) and part_starts == sorted(set(part_starts))
    call_samples, return_samples = defaultdict(Counter), defaultdict(Counter)
    by_kind = Counter()
    generated = 0
    for count, frame, _ in samples:
        if '<unknown binary>' not in frame:
            continue
        assert count > 0 and '...' not in frame
        offsets = [int(a, 16) - mapping['arena_base'] for a in re.findall(r'0x([0-9a-f]+)', frame)]
        assert offsets
        spans = [locate(coarse, starts, o) for o in offsets]
        assert len({(s['function'], s['pc'], s['region_pc'], s['kind']) for s in spans}) == 1
        generated += count
        if spans[0]['kind'] != 'transition':
            continue
        details = [locate(parts, part_starts, o) for o in offsets]
        identities = {(d['function'], d['pc'], d['operation'], d['kind'], d['argument']) for d in details}
        assert len(identities) == 1
        fid, pc, operation, kind, _ = next(iter(identities))
        assert (fid, pc) == (spans[0]['function'], spans[0]['pc'])
        assert operation in ['Call', 'Return']
        by_kind[operation + '/' + kind] += count
        if operation == 'Call':
            call_samples[calls[fid, pc]['callee']][kind] += count
        else:
            return_samples[fid][kind] += count
    return call_samples, return_samples, by_kind, generated


def summarize(profile, calls, mapping, call_samples, return_samples):
    incoming, outgoing, sites = Counter(), Counter(), Counter()
    for (fid, _), call in calls.items():
        incoming[call['callee']] += call['hits']
        outgoing[fid] += call['hits']
        sites[call['callee']] += 1
    emitted = {f['function']: f['end'] - f['offset'] for f in mapping['functions']}
    result = []
    for fid in sorted(incoming.keys() | call_samples.keys() | return_samples.keys()):
        f = profile['functions'][fid]
        native = sum(hits * (f['jit_block_ends'][pc] - pc) for pc, hits in enumerate(f['jit_blocks']) if hits)
        result.append(dict(function=fid, name=f['name'], frame_size=f['frame_size'], registers=f['registers'],
            bytecode_operations=len(f['operations']), emitted_bytes=emitted.get(fid, 0),
            static_native_call_sites=sites[fid], native_incoming_calls=incoming[fid], native_outgoing_calls=outgoing[fid],
            whole_function_native_operations=native, whole_function_interpreted_operations=sum(f['interpreted']),
            rendered_variant_counts=dict(Counter(map(variant, f['operations']))),
            call_samples=sum(call_samples[fid].values()), return_samples=sum(return_samples[fid].values()),
            call_parts=dict(call_samples[fid]), return_parts=dict(return_samples[fid])))
    return sorted(result, key=lambda r: (-r['call_samples']-r['return_samples'], -r['native_incoming_calls'], r['function']))
