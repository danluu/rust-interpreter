"""Independent reconstruction of actual observed LRU transitions; no execution policy."""
from collections import Counter, OrderedDict, defaultdict
import re


class HistoryModel:
    def __init__(self, limit=64*1024**2):
        self.limit=limit
        self.entries=OrderedDict()
        self.charge=512
        self.evictions=0
        self.seen=set()
        self.inserted=set()
        self.functions=defaultdict(set)

    def consume(self, counts, storage):
        assert counts['trace_dropped']==0
        trace=counts['trace']
        assert len(trace)==counts['lookups'] and len(trace)<=4096
        for field,kind in [('hits','hit'),('restore_declines','restore_decline'),('key_declines','key_decline')]:
            assert counts[field]==sum(e['lookup']==kind for e in trace)
        assert counts['inserted']==sum(e['inserted'] for e in trace)
        assert counts['capture_declines']==sum(e['lookup'] in ['miss','restore_decline']
            and e['words']>0 and not e['inserted'] for e in trace)
        assert counts['miss_emit_ns']==sum(e['emission_ns'] for e in trace)
        outcomes=Counter();costs=Counter();misses=[];inserted_code=0;inserted_charge=0
        for e in trace:
            assert e['failed'] is False and type(e['inserted']) is bool
            for field in ['function','charge','code_bytes','emission_ns','words']:
                assert type(e[field]) is int and e[field]>=0
            key=e['key'];lookup=e['lookup'];fid=e['function']
            assert lookup in ['hit','miss','restore_decline','key_decline']
            if lookup=='key_decline':
                assert key is None and not e['inserted']
                reason='key_decline'
            else:
                assert type(key) is str and re.fullmatch('[0-9a-f]{64}',key)
                assert (key in self.entries)==(lookup in ['hit','restore_decline'])
                if key in self.entries:
                    assert self.entries[key][2]==fid
                    self.entries.move_to_end(key)
                if lookup!='miss':reason=lookup
                elif key in self.inserted:reason='evicted_key'
                elif key in self.seen:reason='previously_not_retained'
                elif self.functions[fid]:reason='changed_key'
                else:reason='first_worker_function'
                self.seen.add(key);self.functions[fid].add(key)
            if lookup=='hit':assert not e['inserted'] and e['emission_ns']==0 and e['words']>0
            if e['inserted']:
                assert lookup in ['miss','restore_decline'] and e['words']>0
                charge=e['charge'];code=e['code_bytes']
                assert 0<e['words']*4<=code<=charge<=self.limit-512
                if key in self.entries:self.charge-=self.entries.pop(key)[0]
                while self.charge+charge>self.limit or len(self.entries)>=16384:
                    _,removed=self.entries.popitem(last=False)
                    self.charge-=removed[0];self.evictions+=1
                self.entries[key]=(charge,code,fid);self.charge+=charge;self.inserted.add(key)
                inserted_code+=code;inserted_charge+=charge
            outcomes[reason]+=1;costs[reason]+=e['emission_ns']
            if lookup!='hit':misses.append(dict(e,reason=reason))
        assert self.charge==storage['charged_bytes']
        assert len(self.entries)==storage['entries'] and self.evictions==storage['evictions']
        assert storage['limit_bytes']==self.limit
        return dict(outcomes=dict(outcomes),emission_ns=dict(costs),
            inserted_code_bytes=inserted_code,inserted_charge_bytes=inserted_charge,
            retained_code_bytes=sum(v[1] for v in self.entries.values()),
            most_expensive_misses=sorted(misses,key=lambda e:e['emission_ns'],reverse=True)[:20],
            all_events_reconciled=True)
