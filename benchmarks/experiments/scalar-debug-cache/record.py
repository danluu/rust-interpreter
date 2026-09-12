"""Record the completed debug preservation batch and its rejected lock attempt."""
import fcntl
from pathlib import Path
import run
d=run.driver
ROOT=run.ROOT

def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        d.evidence=run.evidence;d.sources=run.sources
        evidence={};batches=[]
        for action,attempt in [('prepare','02'),('apply','01'),('verify','01')]:
            name=f'scalar-debug-cache-{action}-{attempt}';supervisor=ROOT/'.work/experiments'/name
            controller=ROOT/'.work/scalar-debug-cache-01'/(action+'-'+attempt)
            s,c=d.read(supervisor/'status.json'),d.read(controller/'status.json')
            d.require(s['status']==c['status']=='finished' and s['returncode']==c['returncode']==0
                and s['child_pid']==c['pid'] and s['supervisor_pid']==c['parent_pid'],'batch not terminal')
            d.require(d.sha(supervisor/'plan.json')==s['plan_sha256'] and d.sha(supervisor/'command.log')==s['log_sha256'],
                'batch evidence changed')
            for directory in [supervisor,controller]:
                for p in directory.iterdir():
                    if p.is_file():evidence[str(p.relative_to(ROOT))]=d.sha(p)
            batches.append(dict(action=action,supervisor=s,controller=c))
        rejected=ROOT/'.work/experiments/scalar-debug-cache-prepare-01';s=d.read(rejected/'status.json')
        d.require(s['status']=='finished' and s['returncode']==1 and d.sha(rejected/'command.log')==s['log_sha256']
            and 'BlockingIOError' in (rejected/'command.log').read_text(),'rejected lock attempt differs')
        for p in rejected.iterdir():
            if p.is_file():evidence[str(p.relative_to(ROOT))]=d.sha(p)
        archives=[];proofs={}
        for name in run.CATALOG:
            identity='scalar-debug-'+name+'-01';work,plan,status,target=d.load(identity)
            d.require(status['status']=='completed' and not list(target.iterdir()),'archive not retired')
            d.require(d.sha(work/'cache.zip')==status['archive_sha256'],'archive payload changed')
            for p in [ROOT/'results'/identity/'summary.json',ROOT/'results'/identity/'plan.json',work/'status.json']:
                evidence[str(p.relative_to(ROOT))]=d.sha(p)
            proofs.update(plan['proofs'])
            archives.append(dict(run=name,name=identity,original_bytes=status['unique_original_bytes'],
                archive_bytes=status['archive_bytes'],archive_sha256=status['archive_sha256'],
                files=sum(len(g['paths']) for g in plan['manifest']['groups']),target=str(target.relative_to(ROOT))))
        d.require(all(d.sha(ROOT/p)==h for p,h in proofs.items()),'external evidence changed')
        out=ROOT/'results/scalar-debug-cache-01';out.mkdir(exist_ok=False)
        d.write_json(out/'summary.json',dict(status='passed',archives=archives,archive_count=len(archives),
            original_bytes=sum(a['original_bytes'] for a in archives),archive_bytes=sum(a['archive_bytes'] for a in archives),
            files=sum(a['files'] for a in archives),external_hashes=len(proofs),proofs=proofs,evidence=evidence,
            batches=batches,rejected_lock_attempt=s,all_processes_terminal=True,processes_signaled=0,
            note='All archive payloads were decoded and hashed by the terminal verification batch. Only exact debug targets were retired.'))
        print(dict(status='passed',archives=len(archives),external_hashes=len(proofs)))

if __name__=='__main__':main()
