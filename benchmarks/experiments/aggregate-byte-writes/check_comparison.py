#!/usr/bin/env python3
"""Qualify the isolated changed-exporter verifier without altering prior evidence."""
import copy
import fcntl
from pathlib import Path
from unittest.mock import patch
from build_relocation import ROOT,HERE,PARENT,read,write,sha,require
import verify_relocation as v
import verify_repeated_workflow as base

def expected_tools():
    build=read(ROOT/'results/aggregate-relocation-build-01/summary.json')
    parent=read(ROOT/'results/aggregate-byte-writes-build-02/summary.json')['binaries']
    # The diagnostic exporter differs; bind the production exporter explicitly.
    parent={**parent,'rust-interp-mir-export':'65c11a7d2aacc2941266f3ae9fc90805177a5d82174a4a90d0704e634cba9ad2'}
    return {mode:dict(tool_key=key,vm_sha256=b['rust-interp-vm'],exporter_sha256=b['rust-interp-mir-export'],wrapper_sha256=b['rust-interp-rustc-wrapper'])
        for mode,key,b in [('baseline',PARENT,parent),('candidate',build['tool_key'],build['binaries'])]}

def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        paths=[]
        for run in ['resumable-copy-e2e-01','resumable-copy-original-e2e-01','resumable-bulk-e2e-02']:
            for case in ['folded-literal-trie','token-phrase']:
                path=ROOT/'results'/(run+'-'+case)/'summary.json'
                require(base.verify(read(path))==read(path.with_name('verification.json')),'historical verification differs')
                paths.extend([path,path.with_name('verification.json')])
        report=read(paths[0]);rows_path=ROOT/report['raw']/'records.json';rows=read(rows_path)
        expected=expected_tools();report['comparison']['identical_bytecode_required']=False
        report['tool_builds']['baseline']=copy.deepcopy(report['tool_builds']['candidate'])
        for mode,t in expected.items():
            report['tool_builds'][mode].update({k:t[k] for k in ['tool_key','vm_sha256','exporter_sha256']})
        for row in rows:
            if row['mode']=='native':continue
            for call in row['calls']:
                key=expected[row['mode']]['tool_key'];call['launch']['tool_key']=key
                call['command'][call['command'].index('--tool-key')+1]=key
        original_read=v.read
        def check(r=report,rs=rows,t=expected):
            with patch.object(v,'read',side_effect=lambda path:rs if path==rows_path else original_read(path)):
                return v.verify(r,t)
        require(check()['paired_bytecode_identical'],'equal artifact fixture failed')
        changed=copy.deepcopy(rows);baseline=[r for r in changed if r['mode']=='baseline']
        baseline[0]['artifacts'],baseline[1]['artifacts']=baseline[1]['artifacts'],baseline[0]['artifacts']
        require(not check(rs=changed)['paired_bytecode_identical'],'changed artifacts claimed identical')
        rejected=[]
        index=next(i for i,r in enumerate(rows) if r['mode']=='baseline')
        def reject(name,mutate):
            r,rs,t=copy.deepcopy(report),copy.deepcopy(rows),copy.deepcopy(expected);mutate(r,rs,t)
            try:check(r,rs,t)
            except RuntimeError:rejected.append(name)
            else:raise RuntimeError('accepted '+name)
        reject('missing expected mode',lambda r,s,t:t.pop('candidate'))
        reject('malformed identity',lambda r,s,t:t['candidate'].update(tool_key='bad'))
        reject('different VM',lambda r,s,t:t['candidate'].update(vm_sha256='1'*64))
        reject('different wrapper',lambda r,s,t:t['candidate'].update(wrapper_sha256='1'*64))
        reject('same exporter',lambda r,s,t:t['candidate'].update(exporter_sha256=t['baseline']['exporter_sha256']))
        reject('unbound exporter',lambda r,s,t:r['tool_builds']['candidate'].update(exporter_sha256='1'*64))
        reject('required artifact equality',lambda r,s,t:r['comparison'].update(identical_bytecode_required=True))
        for field in ['jit_resumable_calls','jit_persistent_registers','inline_leaves']:
            reject('changed '+field,lambda r,s,t,f=field:r['tool_builds']['baseline'].update({f:False}))
        reject('different flags',lambda r,s,t:r['tool_builds']['baseline'].update(guest_rustflags=['-Zmir-opt-level=0']))
        reject('both wrong flags',lambda r,s,t:[r['tool_builds'][m].update(guest_rustflags=['-Zmir-opt-level=0']) for m in t])
        reject('executed flags',lambda r,s,t:s[index]['calls'][0].update(rustflags='wrong'))
        reject('launch key',lambda r,s,t:s[index]['calls'][0]['launch'].update(tool_key='1'*64))
        reject('command key',lambda r,s,t:s[index]['calls'][0]['command'].__setitem__(s[index]['calls'][0]['command'].index('--tool-key')+1,'1'*64))
        reject('corrupt artifact',lambda r,s,t:s[index]['artifacts'][0].update(sha256='1'*64))
        reject('missing command',lambda r,s,t:s.pop())
        reject('test source modified',lambda r,s,t:r.update(test_source_unchanged=False))
        reject('wrong edit accepted',lambda r,s,t:r.update(wrong_production_edit_rejected=False))
        paths.extend([Path(__file__),HERE/'verify_relocation.py',ROOT/'scripts/verify_repeated_workflow.py',
            HERE/'RELOCATION-NEXT.md',ROOT/'results/aggregate-relocation-build-01/summary.json'])
        out=ROOT/'results/aggregate-relocation-controls-01';out.mkdir(exist_ok=False)
        write(out/'summary.json',dict(status='passed',historical_reports=6,positive_fixtures=2,rejected=rejected,
            expected_tools=expected,sources={str(p.relative_to(ROOT)):sha(p) for p in paths},performance_measurement=False,
            note='Synthetic fixtures test admission and exact artifact retention only; no prior measured receipt or production verifier was modified.'))
        print(dict(historical_reports=6,positive_fixtures=2,rejected=len(rejected)))

if __name__=='__main__':main()
