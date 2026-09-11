#!/usr/bin/env python3
"""Check independent case controls, ratio gates and complete-cache admission bounds."""
import copy
import fcntl
import math
from pathlib import Path
from build_relocation import ROOT,HERE,read,write,sha,require
from check_comparison import expected_tools
from heldout_controls import ORDER,case,guest_flags,compare_controls,paired
from heldout_space import estimate
from workflow_space import admit

def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        tools=expected_tools();rejected=[];references={};estimates={}
        old=read(ROOT/'results/resumable-copy-heldout-recovery-01/summary.json')
        for label in ORDER:
            c=case(label);prior=next(r for r in old['workflows'] if r['label']==label)
            path=ROOT/'results'/(prior['run_id']+'-'+label)/'summary.json';report=read(path)
            require(guest_flags(c)==report['tool_builds']['candidate']['guest_rustflags'],'case flags differ from independent executed history')
            report['tool_builds']['baseline']=copy.deepcopy(report['tool_builds']['candidate'])
            for mode,t in tools.items():report['tool_builds'][mode].update({k:t[k] for k in ['tool_key','vm_sha256','exporter_sha256']})
            compare_controls(report,c,tools)
            references[str(path.relative_to(ROOT))]=sha(path)
            changes=[('native_control','jobs',4),('native_control','profile','repository'),('native_control','test_threads','1'),
                ('custom_build_jobs','candidate',1),('tool_builds.baseline','inline_leaves',False),
                ('tool_builds.candidate','jit_resumable_calls',False),('tool_builds.candidate','trap_unsupported_calls',
                    not report['tool_builds']['candidate']['trap_unsupported_calls'])]
            for parent,key,value in changes:
                r=copy.deepcopy(report);target=r
                for component in parent.split('.'):target=target[component]
                target[key]=value
                try:compare_controls(r,c,tools)
                except RuntimeError:rejected.append(label+':'+parent+'.'+key)
                else:raise RuntimeError('accepted changed case controls')
            needed,bound=estimate(label);references.update(bound);boundary=needed['minimum_free_bytes']
            require(not admit(boundary-1,needed) and admit(boundary,needed) and
                not admit(boundary-8*1024**3,needed),'admission boundary or running floor differs')
            require(needed['command_floor_bytes']==8*1024**3,'running floor missing')
            estimates[label]=needed
        expected_nu=(13_455_530_541*120+99)//100+8*1024**3+2_901_746_395+268_435_456
        require(estimates['nushell-type-relations']['minimum_free_bytes']==expected_nu and
            estimates['ruff']['minimum_free_bytes']==17_351_777_078,'qualified historical estimate differs')
        # Ratios are paired per edit, not ratios of aggregate medians.
        rows=[dict(cycle=c,state=s,mode=m,seconds=(c+s+1)*10.0,cpu_seconds=(c+s+1)*10.0)
            for c in range(3) for s in range(1,6) for m in ['native','baseline','candidate']]
        for wall,cpu,want in [(1,1,True),(.8,.9,True),(1.05,1,True),(1,1.05,True),(1.051,1,False),(1,1.051,False)]:
            changed=copy.deepcopy(rows)
            for r in changed:
                if r['mode']=='candidate':r['seconds']*=wall;r['cpu_seconds']*=cpu
            result=paired(changed);require(result['passed']==want and abs(result['wall_ratio']-wall)<1e-12 and abs(result['cpu_ratio']-cpu)<1e-12,'gate arithmetic differs')
        for value in [float('nan'),float('inf'),-1,0]:
            changed=copy.deepcopy(rows);changed[0]['seconds']=value
            try:paired(changed)
            except RuntimeError:rejected.append('measurement:'+str(value))
            else:raise RuntimeError('non-finite timing accepted')
        changed=copy.deepcopy(rows);changed.pop()
        try:paired(changed)
        except RuntimeError:rejected.append('missing edited mode')
        else:raise RuntimeError('missing pair accepted')
        paths=[Path(__file__),HERE/'heldout_controls.py',HERE/'heldout_space.py',HERE/'run_heldout.py',HERE/'QUALIFICATION-NEXT.md',
            HERE/'verify_heldouts.py',ROOT/'scripts/workflow_space.py',ROOT/'benchmarks/workflow-corpus.json',
            ROOT/'benchmarks/experiments/resumable-native-calls/preflight_copy_heldout_case.py']
        old_qualification=ROOT/'results/copy-heldout-case-space-01/summary.json';q=read(old_qualification)
        require(q['status']=='passed' and q['invalid_references_rejected']==25 and
            all(sha(ROOT/p)==h for p,h in q['sources'].items()),'historical estimator qualification differs')
        paths.append(old_qualification)
        sources={str(p.relative_to(ROOT)):sha(p) for p in paths}
        require(all(sha(ROOT/p)==h for p,h in references.items()),'reference evidence changed')
        out=ROOT/'results/aggregate-relocation-heldout-admission-01';out.mkdir(exist_ok=False)
        write(out/'summary.json',dict(status='passed',cases=7,ratio_gate_cases=6,rejected=rejected,estimates=estimates,
            exact_space_boundaries=True,missing_running_floor_rejected=True,sources=sources,references=references,
            benchmark_started=False,cache_files_modified=False))
        print(dict(cases=7,ratio_gate_cases=6,rejected=len(rejected)))

if __name__=='__main__':main()
