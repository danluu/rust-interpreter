"""Record a completed fixed workflow's process and evidence identities."""
import argparse
import fcntl
from pathlib import Path
import workflows as workflow


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--phase',choices=['aa','e2e'],required=True)
    parser.add_argument('--case',choices=['folded-literal-trie','token-phrase'],required=True)
    args=parser.parse_args();root=workflow.ROOT;run=workflow.run_id(args.phase,args.case)
    with (root/'.work/benchmark.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        supervisor=root/'.work/experiments'/run;work=root/'.work'/run;out=root/'results'/run
        s=workflow.read(supervisor/'status.json');c=workflow.read(work/'status.json')
        plan=workflow.read(work/'plan.json');a=workflow.read(out/'slot-assessment.json')
        workflow.require(s['status']==c['status']=='finished' and s['returncode']==c['returncode']==0
            and s['child_pid']==c['pid'] and s['supervisor_pid']==c['parent_pid']
            and c['child_returncode']==0 and c['command']==plan['command'],'workflow did not finish normally')
        workflow.require(workflow.sha(supervisor/'plan.json')==s['plan_sha256'] and
            workflow.sha(supervisor/'command.log')==s['log_sha256'],'supervisor evidence changed')
        workflow.require(all(workflow.sha(root/p)==h for p,h in a['evidence'].items()),'assessed evidence changed')
        workflow.require(a['phase']==args.phase and a['label']==args.case and len(a['pairs'])==15,'assessment identity differs')
        report=workflow.read(out/'summary.json');raw=root/report['raw']
        paths=[Path(__file__),out/'summary.json',out/'slot-assessment.json']
        paths += [supervisor/n for n in ['plan.json','status.json','command.log']]
        paths += [work/n for n in ['plan.json','status.json','admission.json','command.log']]
        paths += [raw/n for n in ['records.json','check-records.json','source-transitions.json']]
        workflow.require(not (out/'execution.json').exists(),'execution receipt already exists')
        workflow.write(out/'execution.json',dict(supervisor=s,controller=c,
            evidence={str(p.relative_to(root)):workflow.sha(p) for p in paths}))
        print({k:a[k] for k in ['phase','label','wall_ratio','cpu_ratio','passed']})


if __name__ == '__main__': main()
