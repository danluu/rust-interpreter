import unittest
from model import HistoryModel


def event(key, function, lookup='miss', inserted=True, charge=200):
    return dict(key=key*64,function=function,lookup=lookup,inserted=inserted,
        charge=charge if inserted else 0,code_bytes=80 if inserted else 0,
        emission_ns=0 if lookup=='hit' else 10,words=20,failed=False)


def counts(*events):
    return dict(trace=list(events),trace_dropped=0,lookups=len(events),
        hits=sum(e['lookup']=='hit' for e in events),
        restore_declines=sum(e['lookup']=='restore_decline' for e in events),
        key_declines=sum(e['lookup']=='key_decline' for e in events),
        inserted=sum(e['inserted'] for e in events),
        capture_declines=sum(e['lookup'] in ['miss','restore_decline'] and e['words']>0 and not e['inserted'] for e in events),
        miss_emit_ns=sum(e['emission_ns'] for e in events))


def storage(entries,charge,evictions=0):
    return dict(entries=entries,charged_bytes=charge,evictions=evictions,limit_bytes=1024)


class ModelTests(unittest.TestCase):
    def test_actual_recency_eviction_and_changed_key_are_distinct(self):
        m=HistoryModel(1024)
        m.consume(counts(event('a',0),event('b',1)),storage(2,912))
        m.consume(counts(event('a',0,'hit',False),event('c',2)),storage(2,912,1))
        row=m.consume(counts(event('b',1)),storage(2,912,2))
        self.assertEqual(row['outcomes'],{'evicted_key':1})
        row=m.consume(counts(event('d',0)),storage(2,912,3))
        self.assertEqual(row['outcomes'],{'changed_key':1})
        self.assertEqual(row['retained_code_bytes'],160)

    def test_restore_decline_replaces_existing_charge(self):
        m=HistoryModel(1024);m.consume(counts(event('a',0)),storage(1,712))
        row=m.consume(counts(event('a',0,'restore_decline',True,300)),storage(1,812))
        self.assertEqual(row['outcomes'],{'restore_decline':1})

    def test_previously_declined_capture_is_not_called_eviction(self):
        m=HistoryModel(1024)
        m.consume(counts(event('a',0,inserted=False)),storage(0,512))
        row=m.consume(counts(event('a',0)),storage(1,712))
        self.assertEqual(row['outcomes'],{'previously_not_retained':1})

    def test_hit_without_prior_insertion_is_rejected(self):
        with self.assertRaises(AssertionError):
            HistoryModel(1024).consume(counts(event('a',0,'hit',False)),storage(0,512))

    def test_dropped_trace_and_counter_tampering_are_rejected(self):
        for field in ['trace_dropped','lookups','hits','miss_emit_ns','inserted','capture_declines']:
            row=counts(event('a',0));row[field]+=1
            with self.subTest(field=field),self.assertRaises(AssertionError):
                HistoryModel(1024).consume(row,storage(1,712))

    def test_storage_tampering_is_rejected(self):
        for field in ['entries','charged_bytes','evictions','limit_bytes']:
            row=storage(1,712);row[field]+=1
            with self.subTest(field=field),self.assertRaises(AssertionError):
                HistoryModel(1024).consume(counts(event('a',0)),row)

    def test_failed_or_malformed_event_is_rejected(self):
        for field,value in [('key','z'*64),('failed',True),('function',True),('charge',9999),('emission_ns',-1)]:
            row=event('a',0);row[field]=value
            with self.subTest(field=field),self.assertRaises(AssertionError):
                HistoryModel(1024).consume(counts(row),storage(1,712))


if __name__=='__main__':unittest.main()
