"""Validate schema-2 ownership plus explicit branch-budget refund thunks."""
from bisect import bisect_right
from collections import Counter
import hashlib

KINDS = {'entry', 'range_guard', 'budget', 'profile', 'operation', 'flush', 'region_exit',
         'fault_tail', 'assertion_tail', 'budget_fallback', 'successor_fallback', 'transition', 'scalar_leaf', 'budget_edge'}


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
    integer(operation_map['arena_base'])
    assert bool(operation_map['arena_base']) == bool(code)
    region_by_key, expected = {}, set()
    cursor = 0
    for row in regions['ranges']:
        assert row['kind'] in {'ordinary_region', 'resumable_region', 'resumable_call', 'resumable_return', 'scalar_leaf'}
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
    assert functions == {(fid,pc is None) for fid,pc in region_by_key}
    assert sum(static.values()) * 4 == len(code)
    edges=validate_budget_edges(operation_map,regions,code)
    return dict(budget_edges=edges,rows=rows, starts=[r['offset'] for r in rows], static_words=dict(static),
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


def validate_budget_edges(operation_map,regions,code):
    """Check positive-refund thunks; zero-refund direct links are not certified here."""
    ranges=regions['ranges'];starts=[r['offset'] for r in ranges]
    spans={}
    for f in operation_map['functions']:
        for row in f['spans']:
            spans.setdefault((f['function'],row['region_pc']),[]).append(row)
    def word(at):return int.from_bytes(code[at:at+4],'little')
    def credit(region):
        budget,=[r for r in spans[region['function'],region['pc']] if r['kind']=='budget']
        assert budget['end']-budget['offset']==16,'unexpected reservation guard encoding'
        at=budget['offset'];mov,cmp,branch,sub=[word(at+i*4) for i in range(4)]
        assert mov&~(0xffff<<5)==0xd280000a and cmp==0xeb0a02df and sub==0xcb0a02d6
        assert branch&0xff00001f==0x54000003
        steps=(mov>>5)&0xffff;cost=region['pc_end']-region['pc']
        assert 1<=cost<=1024 and cost<=steps<=4096
        return steps,cost,budget['end']
    edges=[]
    for f in operation_map['functions']:
        for row in f['spans']:
            if row['kind']!='budget_edge':continue
            assert operation_map['resumable_calls'] and row['pc'] is None
            at=row['offset'];assert row['end']==at+8
            add,branch=word(at),word(at+4)
            assert add&~0x003ffc00==0x910002d6,'refund must preserve NZCV and only change x22'
            refund=(add>>10)&4095;assert refund>0 and branch>>26==5
            displacement=branch&0x3ffffff
            if displacement&(1<<25):displacement-=1<<26
            target=at+4+displacement*4
            assert 0<=target<len(code) and target%4==0
            source=ranges[bisect_right(starts,at)-1];dest=ranges[bisect_right(starts,target)-1]
            assert source['function']==dest['function']==f['function']
            assert source['pc']==row['region_pc'] and source['kind']=='resumable_region'
            steps,cost,_=credit(source);suffix=steps-cost
            if dest['kind']=='resumable_region':
                target_steps,_,fast_entry=credit(dest)
                dest_spans=spans[dest['function'],dest['pc']]
                entry,=[r for r in dest_spans if r['kind']=='entry']
                if target==fast_entry:
                    assert dest['pc']>source['pc'] and not any(r['kind']=='range_guard' for r in dest_spans)
                    assert refund==suffix-target_steps;mode='fast'
                else:
                    assert target==entry['end'] and refund==suffix;mode='checked'
            else:
                assert dest['kind'] in ['resumable_call','resumable_return']
                assert target+8<=dest['end'] and word(target)==0xeb1f02df and word(target+4)&0xff00001f==0x54000000
                assert refund==suffix;mode='transition'
            edges.append(dict(offset=at,function=f['function'],source_pc=source['pc'],
                              target_pc=dest['pc'],target_offset=target,mode=mode,refund=refund))
    return edges
