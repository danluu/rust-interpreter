"""Join exact region publication to charged entries; infer no execution order."""
from collections import Counter
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'benchmarks/experiments/native-continuation-snapshot-workflows'))
from native_observation import logical_counts


def analyze(profile, mapping):
    _, logical = logical_counts(profile)
    functions = profile['functions']
    assert all(not any(f[k]) for f in functions
               for k in ['jit_tree_blocks', 'jit_tree_block_ends'])
    assert mapping['schema_version'] == 1 and mapping['architecture'] == 'aarch64'
    assert mapping['byte_order'] == 'little' and mapping['profiled']
    assert mapping['resumable_calls'] and not mapping['native_call_stubs']
    cursor = 0
    seen = set()
    covered = {fid: set() for fid in range(len(functions))}
    totals = Counter()
    by_function = {}
    details = []
    charged_ops = scalar_bytes = 0
    for region in mapping['ranges']:
        fid = region['function']
        assert type(fid) is int and 0 <= fid < len(functions)
        f = functions[fid]
        assert region['name'] == f['name']
        assert region['offset'] == cursor and cursor < region['end'] <= mapping['code_bytes']
        assert region['end'] % 4 == 0
        size = region['end'] - cursor
        cursor = region['end']
        if region['kind'] == 'scalar_leaf':
            assert region['pc'] is None and region['pc_end'] is None
            assert (fid, None) not in seen
            seen.add((fid, None))
            bucket = 'scalar_executed' if any(f.get('jit_scalar_hits', [])) else 'scalar_no_hits'
            totals[bucket+'_bytes'] += size
            totals[bucket+'_bodies'] += 1
            scalar_bytes += size
            continue
        assert region['kind'] in {'resumable_region', 'resumable_call', 'resumable_return'}
        pc, end = region['pc'], region['pc_end']
        assert type(pc) is int and type(end) is int and 0 <= pc < end <= len(f['operations'])
        assert (fid, pc) not in seen and not covered[fid].intersection(range(pc, end))
        seen.add((fid, pc))
        covered[fid].update(range(pc, end))
        assert f['jit_block_ends'][pc] == end
        hits = f['jit_blocks'][pc]
        interpreted = sum(f['interpreted'][pc:end])
        bucket = 'charged' if hits else 'interpreted_only' if interpreted else 'no_recorded_work'
        totals[bucket+'_regions'] += 1
        totals[bucket+'_bytes'] += size
        totals[bucket+'_bytecode_operations'] += end-pc
        totals['ordinary_regions'] += 1
        totals['ordinary_bytes'] += size
        totals['ordinary_charged_entries'] += hits
        charged_ops += hits*(end-pc)
        item = by_function.setdefault(fid, dict(function=fid, name=f['name'],
            bytecode_operations=len(f['operations']), regions=0, bytes=0,
            charged_regions=0, charged_bytes=0, no_recorded_work_regions=0,
            no_recorded_work_bytes=0, interpreted_only_regions=0, interpreted_only_bytes=0))
        item['regions'] += 1
        item['bytes'] += size
        item[bucket+'_regions'] += 1
        item[bucket+'_bytes'] += size
        details.append(dict(function=fid, pc=pc, pc_end=end, kind=region['kind'],
            bytes=size, native_hits=hits, interpreted_operations=interpreted, bucket=bucket))
    assert cursor == mapping['code_bytes'] == totals['ordinary_bytes'] + scalar_bytes
    for fid, f in enumerate(functions):
        for pc, end in enumerate(f['jit_block_ends']):
            assert bool(end) == ((fid, pc) in seen), 'missing or invented published region'
        if any(f.get('jit_scalar_hits', [])):
            assert (fid, None) in seen, 'scalar counters without body'
    assert charged_ops + logical['scalar'] == logical['native']
    totals['ordinary_functions'] = len(by_function)
    totals['ordinary_charged_operations'] = charged_ops
    totals['all_bytes'] = cursor
    rows = sorted(by_function.values(), key=lambda f: (-f['no_recorded_work_bytes'], f['function']))
    return dict(totals=dict(totals), logical_counts=logical,
                functions=rows, regions=details)
