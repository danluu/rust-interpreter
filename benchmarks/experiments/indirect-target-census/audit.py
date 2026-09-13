"""Bind observer builds, admission failure and exact original-case observations."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import require_space,write_json as write


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--run-id',required=True)
    args=parser.parse_args();assert re.fullmatch(r'indirect-target-census-\d{2}',args.run_id)
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,12)
        evidence={};frozen={};bindings={}
        revision=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
        def read(path):
            evidence[path]=sha(ROOT/path);return json.loads((ROOT/path).read_text())
        def terminal(name,saved,code):
            outer='.work/experiments/'+name+'/'
            t=read(saved);assert t==read(outer+'status.json')
            assert t['status']=='finished' and t['returncode']==code and t['owner']==t['cwd']==str(ROOT)
            assert sha(ROOT/outer/'plan.json')==t['plan_sha256'] and sha(ROOT/outer/'command.log')==t['log_sha256']
            read(outer+'plan.json');evidence[outer+'command.log']=t['log_sha256']
        def inputs(plan,historical=False):
            for p,h in plan['frozen'].items():
                if historical:
                    spec=plan['source_revision']+':'+p
                    assert hashlib.sha256(subprocess.check_output(['git','show',spec])).hexdigest()==h,p
                    bindings[spec]=h
                else:
                    assert sha(ROOT/p)==h,p;assert frozen.setdefault(p,h)==h,p
        for name,code in [('indirect-target-build-01',1),('indirect-target-build-02',0)]:
            s=read('results/'+name+'/summary.json');raw=s['raw']
            for key in ['plan','records']:assert sha(ROOT/raw/(key+'.json'))==s[key+'_sha256']
            inputs(read(raw+'/plan.json'),historical=bool(code));records=read(raw+'/records.json')
            terminal(name,'results/'+name+'/terminal.json',code)
            if code:
                assert s['tests_executed']==s['guest_commands']==0 and not s['release_started']
                assert len(records)==1 and records[0]['returncode']!=0 and 'no field' in records[0]['stderr']
            else:
                assert s['tests']==dict(debug=417,release=417) and s['observer_only']
                assert [(r['label'],r['returncode']) for r in records]==[('debug',0),('release',0),('observer',0)]
                for row in records[:2]:
                    assert sum(map(int,re.findall(r'test result: ok\. (\d+) passed;',row['stdout'])))==417
                    assert sum(map(int,re.findall(r'test result: ok\. \d+ passed; \d+ failed; (\d+) ignored;',row['stdout'])))==11
                assert sha(ROOT/s['observer'])==s['observer_sha256'];frozen[s['observer']]=s['observer_sha256']
                observer_hash=s['observer_sha256']
        admission=read('results/indirect-target-admission-01/summary.json')
        assert admission['status']=='not_admitted' and admission['guest_commands']==0 and not admission['inner_directory_created']
        assert not (ROOT/'.work/indirect-target-census-01').exists()
        terminal('indirect-target-census-01','results/indirect-target-admission-01/terminal.json',1)
        output=ROOT/'results'/args.run_id;s=read(str((output/'summary.json').relative_to(ROOT)))
        assert s['status']=='passed' and s['guest_commands']==2 and s['observer_sha256']==observer_hash
        assert s['exact_adopted_code'] and s['exact_per_pc_counts'] and s['exact_counts_memory_entropy']
        raw=s['raw'];assert sha(ROOT/raw/'plan.json')==s['plan_sha256'] and sha(ROOT/raw/'records.json')==s['records_sha256']
        inputs(read(raw+'/plan.json'));records=read(raw+'/records.json')
        assert [r['index'] for r in records]==[0,1] and all(r['returncode']==0 for r in records)
        terminal(args.run_id,str((output/'terminal.json').relative_to(ROOT)),0)
        for c,row in zip(s['comparisons'],records):
            i=c['index'];a=c['attribution'];assert a['calls']==[1025947,843776][i]
            for suffix,key in [('profile.json','profile_sha256'),('trace.json','trace_sha256'),
                ('code/map.json','code_map_sha256'),('code/operations.json','operation_map_sha256'),('code/code.bin','code_sha256')]:
                p=raw+'/'+str(i)+'-'+suffix;assert sha(ROOT/p)==c[key];evidence[p]=c[key]
            report=read(raw+'/'+str(i)+'-trace.json');assert report['pid']==row['pid'] and report['guest_commands']==1
            assert not report['overflow'] and len(report['rows'])==a['rows']
            assert sum(r['count'] for r in report['rows'])==sum(t['calls'] for t in a['sites_by_calls'])==a['calls']
            for n in [1,2,4]:assert a['coverage'][str(n)]==sum(t['calls'] for t in a['sites_by_calls'] if t['target_count']<=n)
        for p,h in frozen.items():
            if p.startswith('.work/'):continue
            spec=revision+':'+p;assert hashlib.sha256(subprocess.check_output(['git','show',spec])).hexdigest()==h,p
            bindings[spec]=h
        write(output/'source-bindings.json',bindings)
        write(output/'closure.json',dict(status='passed',frozen_inputs=len(frozen),git_bound_files=len(bindings),frozen=frozen,
            evidence=evidence,source_bindings_sha256=sha(output/'source-bindings.json'),auditor_sha256=sha(Path(__file__)),
            retained_guest_commands=2,new_guest_commands=0,failed_builds=1,failed_admissions=1,performance_measurement=False))
        print('Closed:',len(frozen),'frozen inputs;',len(bindings),'Git bindings',flush=True)


if __name__=='__main__':main()
