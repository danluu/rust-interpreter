"""Validate same-process operation maps and join PCs to a retained exact profile."""
from bisect import bisect_right
from collections import Counter
import hashlib

KINDS = {'entry', 'range_guard', 'budget', 'profile', 'operation', 'flush', 'region_exit',
         'fault_tail', 'assertion_tail', 'budget_fallback', 'successor_fallback', 'transition'}


def integer(value):
    assert type(value) is int and value >= 0, 'invalid map integer'
    return value


def validate(operation_map, regions, code, profile, pid):
    assert operation_map['schema_version'] == regions['schema_version'] == 1
    assert regions['architecture'] == 'aarch64' and regions['byte_order'] == 'little'
    assert operation_map['complete'] is True and operation_map['reconstructed_bytes_match'] is True
    assert operation_map['pid'] == regions['pid'] == pid
    assert len(code) <= 16 * 1024**2 and len(code) % 4 == 0
    assert operation_map['code_bytes'] == regions['code_bytes'] == len(code)
    assert operation_map['code_sha256'] == hashlib.sha256(code).hexdigest()
    assert not regions['native_call_stubs']
    for key in ['arena_base', 'profiled', 'persistent_registers', 'resumable_calls']:
        assert operation_map[key] == regions[key], ('option mismatch', key)
    for key in ['profiled', 'persistent_registers', 'resumable_calls']:
        assert type(operation_map[key]) is bool
    integer(operation_map['arena_base'])
    assert bool(operation_map['arena_base']) == bool(code)
    region_by_key, expected = {}, set()
    cursor = 0
    for row in regions['ranges']:
        assert row['kind'] in {'ordinary_region', 'resumable_region', 'resumable_call', 'resumable_return'}
        assert row['offset'] == cursor and integer(row['end']) > cursor and row['end'] % 4 == 0
        fid, pc, pc_end = [integer(row[k]) for k in ['function', 'pc', 'pc_end']]
        f = profile['functions'][fid]
        assert row['name'] == f['name'] and pc < pc_end <= len(f['operations'])
        assert f['jit_block_ends'][pc] == pc_end, 'retained profile has different native boundaries'
        assert (fid, pc) not in region_by_key
        region_by_key[fid, pc] = row
        for op in range(pc, pc_end):
            assert (fid, op) not in expected
            expected.add((fid, op))
        cursor = row['end']
    assert cursor == len(code)
    rows, seen, functions = [], set(), set()
    cursor = assertion_end = span_count = 0
    static = Counter()
    for function in operation_map['functions']:
        fid = integer(function['function'])
        assert fid not in functions
        functions.add(fid)
        f = profile['functions'][fid]
        assert function['name'] == f['name'] and function['offset'] == cursor
        assert integer(function['end']) > cursor and function['end'] <= len(code)
        assert function['assertion_base'] == assertion_end
        assertion_end += integer(function['assertion_count'])
        for row in function['spans']:
            span_count += 1
            assert span_count <= 2_000_000
            assert row['kind'] in KINDS
            assert row['offset'] == cursor and integer(row['end']) >= cursor and row['end'] % 4 == 0
            assert row['end'] <= function['end']
            region = region_by_key[fid, integer(row['region_pc'])]
            assert region['offset'] <= cursor <= row['end'] <= region['end']
            pc = row['pc']
            if pc is None:
                assert row['kind'] not in {'operation', 'transition'} and row['end'] > cursor
                label = row['kind']
            else:
                integer(pc)
                assert row['kind'] in {'operation', 'transition'}
                assert region['pc'] <= pc < region['pc_end'] and (fid, pc) not in seen
                seen.add((fid, pc))
                variant = f['operations'][pc].split(' ', 1)[0]
                assert variant and variant.isalnum(), 'invalid retained opcode rendering'
                if row['kind'] == 'transition':
                    assert variant in {'Call', 'Return'} and operation_map['resumable_calls']
                label = row['kind'] + ':' + variant
            words = (row['end'] - cursor) // 4
            static[label] += words
            if words:
                rows.append(dict(offset=cursor, end=row['end'], function=fid, region_pc=row['region_pc'],
                                 pc=pc, kind=row['kind'], label=label))
            cursor = row['end']
        assert cursor == function['end']
    assert cursor == len(code) and span_count == operation_map['spans'] and seen == expected
    assert functions == {fid for fid, _ in region_by_key}
    assert sum(static.values()) * 4 == len(code)
    return dict(rows=rows, starts=[r['offset'] for r in rows], static_words=dict(static),
                spans=span_count, mapped_pcs=len(seen), assertions=assertion_end)


def locate(index, offset):
    position = bisect_right(index['starts'], offset) - 1
    assert position >= 0, 'sample before published code'
    row = index['rows'][position]
    assert row['offset'] <= offset < row['end'] and offset % 4 == 0, 'sample outside mapped word'
    return row
