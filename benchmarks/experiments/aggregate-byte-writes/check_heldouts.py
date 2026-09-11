#!/usr/bin/env python3
"""Qualify per-case compiler admission against actual histories and corrupt fixtures."""
import copy
import fcntl
from pathlib import Path
from unittest.mock import patch
from build_relocation import ROOT,HERE,read,write,sha,require
from check_comparison import expected_tools
import verify_heldouts as v
import verify_relocation as primary
import verify_repeated_workflow as base

FLAGS=['-Zmir-opt-level=3','-Zinline-mir-threshold=400','-Zinline-mir-hint-threshold=800','-Zinline-mir-forwarder-threshold=240']

def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        evidence={};expected=expected_tools();actual=[];positive=[];rejected=[]
        for label in ['folded-literal-trie','token-phrase']:
            path=ROOT/'results'/('aggregate-relocation-e2e-01-'+label)/'summary.json';r=read(path)
            require(v.verify(r,expected,FLAGS)==primary.verify(r,expected),'primary verification differs')
            actual.append(str(path.relative_to(ROOT)));evidence[str(path.relative_to(ROOT))]=sha(path)
        collection_path=ROOT/'results/resumable-copy-heldout-recovery-01/summary.json'
        collection=read(collection_path)
        require(len(collection['workflows'])==7 and not collection['wall_regressions_above_5_percent'] and
            not collection['cpu_regressions_above_5_percent'],'prior heldout corpus incomplete')
        reports=[]
        for case in collection['workflows']:
            path=ROOT/'results'/(case['run_id']+'-'+case['label'])/'summary.json';report=read(path)
            require(base.verify(report)==read(path.with_name('verification.json')),'historical heldout verification differs')
            reports.append((case['label'],report));actual.append(str(path.relative_to(ROOT)));evidence[str(path.relative_to(ROOT))]=sha(path)
        for label,original in reports:
            r=copy.deepcopy(original);records_path=ROOT/r['raw']/'records.json';rows=read(records_path)
            r['comparison']['identical_bytecode_required']=False
            r['tool_builds']['baseline']=copy.deepcopy(r['tool_builds']['candidate'])
            for mode,t in expected.items():r['tool_builds'][mode].update({k:t[k] for k in ['tool_key','vm_sha256','exporter_sha256']})
            for row in rows:
                if row['mode']=='native':continue
                for call in row['calls']:
                    key=expected[row['mode']]['tool_key'];call['launch']['tool_key']=key
                    call['command'][call['command'].index('--tool-key')+1]=key
                    for field,flag in [('jit_persistent_registers','--jit-persistent-registers'),('jit_resumable_calls','--jit-resumable-calls')]:
                        call['launch'][field]=True
                        if flag not in call['command']:call['command'].append(flag)
            flags=FLAGS if label in ['forward-anchored-tls','pgrust-sha1-inline8'] else []
            original_read=v.read
            def check(report=r,records=rows,bound=flags,tools=expected):
                with patch.object(v,'read',side_effect=lambda path:records if path==records_path else original_read(path)):
                    return v.verify(report,tools,bound)
            require(check()['exact_artifact_hashes_verified']==42,'synthetic admission coverage differs')
            positive.append(label)
            index=next(i for i,row in enumerate(rows) if row['mode']=='baseline')
            def reject(name,mutate):
                a,b,c,d=copy.deepcopy(r),copy.deepcopy(rows),copy.deepcopy(flags),copy.deepcopy(expected)
                bound=mutate(a,b,c,d)
                if bound is not None:c=bound
                try:check(a,b,c,d)
                except RuntimeError:rejected.append(dict(case=label,control=name))
                else:raise RuntimeError('accepted corrupt fixture: '+label+'/'+name)
            reject('wrong bound flags',lambda a,b,c,d:c.append('-Zmir-opt-level=2'))
            reject('bound flags not list',lambda a,b,c,d:{'bad':'flags'})
            reject('empty bound token',lambda a,b,c,d:c.append(''))
            reject('whitespace bound token',lambda a,b,c,d:c.append('-Zbad value'))
            reject('executed flags',lambda a,b,c,d:b[index]['calls'][0].update(rustflags='wrong'))
            reject('launch key',lambda a,b,c,d:b[index]['calls'][0]['launch'].update(tool_key='0'*64))
            reject('command key',lambda a,b,c,d:b[index]['calls'][0]['command'].__setitem__(b[index]['calls'][0]['command'].index('--tool-key')+1,'0'*64))
            reject('VM mismatch',lambda a,b,c,d:d['candidate'].update(vm_sha256='0'*64))
            reject('wrapper mismatch',lambda a,b,c,d:d['candidate'].update(wrapper_sha256='0'*64))
            reject('runtime mismatch',lambda a,b,c,d:a['tool_builds']['baseline'].update(jit_resumable_calls=False))
            reject('required equality',lambda a,b,c,d:a['comparison'].update(identical_bytecode_required=True))
            reject('artifact corruption',lambda a,b,c,d:b[index]['artifacts'][0].update(sha256='0'*64))
            reject('accepted wrong edit',lambda a,b,c,d:a.update(wrong_production_edit_rejected=False))
            reject('changed test source',lambda a,b,c,d:a.update(test_source_unchanged=False))
            reject('missing command',lambda a,b,c,d:(b.pop(),None)[1])
        for p in [Path(__file__),HERE/'verify_heldouts.py',HERE/'verify_relocation.py',HERE/'check_comparison.py',
                  ROOT/'scripts/verify_repeated_workflow.py',collection_path,HERE/'QUALIFICATION-NEXT.md']:
            evidence[str(p.relative_to(ROOT))]=sha(p)
        out=ROOT/'results/aggregate-relocation-heldout-controls-01';out.mkdir(exist_ok=False)
        write(out/'summary.json',dict(status='passed',actual_reports=actual,synthetic_admissions=positive,rejected=rejected,
            evidence=evidence,expected_tools=expected,performance_measurement=False,
            private_output='aggregate identities and counts only',prior_sources_and_receipts_unchanged=True))
        print(dict(actual_reports=len(actual),synthetic_admissions=len(positive),rejected=len(rejected)))

if __name__=='__main__':main()
