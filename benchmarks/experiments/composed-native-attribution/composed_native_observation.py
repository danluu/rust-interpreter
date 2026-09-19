"""Validate schema-2 scalar/ordinary code ownership and exact original-PC counts."""
from bisect import bisect_right
from collections import Counter
import hashlib

KINDS = {'entry', 'range_guard', 'budget', 'profile', 'operation', 'flush', 'region_exit',
         'fault_tail', 'assertion_tail', 'budget_fallback', 'successor_fallback', 'transition', 'scalar_leaf'}


def integer(value):
    assert type(value) is int and value >= 0, 'invalid map integer'
    return value


def validate(operation_map, regions, code, profile, pid):
    assert operation_map['schema_version'] == 2 and regions['schema_version'] == 1
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
    indirect=operation_map.get('indirect_calls',False)
    assert type(indirect) is bool and type(regions.get('indirect_calls',False)) is bool
    assert indirect==regions.get('indirect_calls',False)
    assert not indirect or operation_map['resumable_calls']
    integer(operation_map['arena_base'])
    assert bool(operation_map['arena_base']) == bool(code)
    region_by_key, expected = {}, set()
    cursor = 0
    for row in regions['ranges']:
        assert row['kind'] in {'ordinary_region', 'resumable_region', 'resumable_call', 'resumable_return', 'resumable_indirect_call', 'scalar_leaf'}
        assert row['offset'] == cursor and integer(row['end']) > cursor and row['end'] % 4 == 0
        fid=integer(row['function']);assert fid<len(profile['functions'])
        if row['kind']=='scalar_leaf':
            assert row['pc'] is None and row['pc_end'] is None
            f=profile['functions'][fid]
            assert row['name']==f['name'] and 0<len(f['operations'])<=512
            assert (fid,None) not in region_by_key
            region_by_key[fid,None]=row;cursor=row['end'];continue
        pc, pc_end = [integer(row[k]) for k in ['pc', 'pc_end']]
        f = profile['functions'][fid]
        assert row['name'] == f['name'] and pc < pc_end <= len(f['operations'])
        if row['kind']=='resumable_indirect_call':
            assert indirect and pc_end==pc+1 and f['operations'][pc].split(' ',1)[0]=='CallIndirect'
            # The older control VM interpreted this transition. Its zero native
            # end is expected; the current same-process dump owns this one PC.
            assert f['jit_block_ends'][pc] in [0,pc_end]
        else:
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
        scalar=len(function['spans'])==1 and function['spans'][0]['kind']=='scalar_leaf'
        key=(fid,scalar);assert key not in functions;functions.add(key)
        if scalar:assert function['assertion_count']==0
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
            if scalar:
                assert row['kind']=='scalar_leaf' and row['pc'] is None and row['region_pc']==0
                region=region_by_key[fid,None]
                assert region['offset']==function['offset'] and region['end']==function['end']
            else:
                assert row['kind']!='scalar_leaf'
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
                if variant=='CallIndirect' or region['kind']=='resumable_indirect_call':
                    assert variant=='CallIndirect' and row['kind']=='transition' and indirect
                    assert region['kind']=='resumable_indirect_call'
                if row['kind'] == 'transition':
                    assert variant in {'Call', 'Return', 'CallIndirect'} and operation_map['resumable_calls']
                label = row['kind'] + ':' + variant
            words = (row['end'] - cursor) // 4
            static[label] += words
            if words:
                rows.append(dict(offset=cursor, end=row['end'], function=fid, region_pc=row['region_pc'],
                                 pc=pc, kind=row['kind'], label=label))
            cursor = row['end']
        assert cursor == function['end']
    assert cursor == len(code) and span_count == operation_map['spans'] and seen == expected
    assert functions == {(fid,pc is None) for fid,pc in region_by_key}
    assert sum(static.values()) * 4 == len(code)
    return dict(rows=rows, starts=[r['offset'] for r in rows], static_words=dict(static),
                spans=span_count, mapped_pcs=len(seen), assertions=assertion_end)


def locate(index, offset):
    position = bisect_right(index['starts'], offset) - 1
    assert position >= 0, 'sample before published code'
    row = index['rows'][position]
    assert row['offset'] <= offset < row['end'] and offset % 4 == 0, 'sample outside mapped word'
    return row


def logical_counts(profile):
    result=[];native=interpreted=scalar_total=0
    assert isinstance(profile['functions'],list) and len(profile['functions'])<=100_000
    for f in profile['functions']:
        n=len(f['operations']);assert n<=1_000_000
        def vector(key,default=None):
            v=f.get(key,default);assert isinstance(v,list) and len(v)==n
            assert all(type(x) is int and 0<=x<2**64 for x in v),key
            return v
        plain=vector('interpreted');scalar=vector('jit_scalar_hits',[0]*n)
        row=[a+b for a,b in zip(plain,scalar)];interpreted+=sum(plain);native+=sum(scalar);scalar_total+=sum(scalar)
        for hit_key,end_key in [('jit_blocks','jit_block_ends'),('jit_tree_blocks','jit_tree_block_ends')]:
            hits=vector(hit_key);ends=vector(end_key);delta=[0]*(n+1)
            for pc,(count,end) in enumerate(zip(hits,ends)):
                assert end==0 or pc<end<=n
                if count:
                    assert end!=0
                    delta[pc]+=count;delta[end]-=count;native+=count*(end-pc)
            active=0
            for pc in range(n):active+=delta[pc];row[pc]+=active
            assert active+delta[n]==0
        assert all(x<2**64 for x in row)
        result.append(row)
    assert sum(map(sum,result))==native+interpreted
    return result,dict(native=native,interpreted=interpreted,scalar=scalar_total,total=native+interpreted)


def exact_logical_counts(current,prior):
    assert len(current['functions'])==len(prior['functions'])
    for a,b in zip(current['functions'],prior['functions']):
        for key in ['name','frame_size','registers','operations']:assert a[key]==b[key]
    counts,totals=logical_counts(current);baseline,_=logical_counts(prior)
    assert counts==baseline,'original-PC logical counts changed'
    return totals
