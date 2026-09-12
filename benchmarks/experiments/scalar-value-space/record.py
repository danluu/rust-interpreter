"""Close the already verified sixteen-cache preservation batch."""
import fcntl
import os
import subprocess
import batch
from runtime import ROOT, driver as d


def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        evidence={};proofs={};archives=[]
        for action in ['prepare','apply','verify']:
            supervisor=ROOT/'.work/experiments'/f'scalar-budget-cache-{action}-01'
            work=batch.BASE/action;s=d.read(supervisor/'status.json');c=d.read(work/'status.json')
            records=d.read(work/'records.json')
            d.require(s['status']==c['status']=='finished' and s['returncode']==c['returncode']==0
                and len(records)==c['completed']==16 and all(r['returncode']==0 for r in records),'batch not terminal')
            d.require(d.sha(supervisor/'plan.json')==s['plan_sha256'] and d.sha(supervisor/'command.log')==s['log_sha256'],'supervision changed')
            d.require([(r['name'],r['selection']) for r in records]==batch.entries(),'batch selection changed')
            for r in records:d.require(d.sha(work/(r['name']+'.log'))==r['log_sha256'],'child log changed')
            for folder in [supervisor,work]:
                for p in folder.iterdir():
                    if p.is_file():evidence[str(p.relative_to(ROOT))]=d.sha(p)
        for name,selection in batch.entries():
            p=ROOT/'results'/name/'plan.json';s=ROOT/'results'/name/'summary.json'
            plan,status=d.read(p),d.read(s);target=ROOT/status['target'];archive=ROOT/status['archive']
            d.require(status['status']=='completed' and not list(target.iterdir()) and plan['run']==selection,'retirement differs')
            d.require(d.sha(p)==status['plan_sha256'] and d.sha(archive)==status['archive_sha256'],'archive binding differs')
            committed=subprocess.check_output(['git','show','4df362f:'+str(p.relative_to(ROOT))],cwd=ROOT)
            d.require(committed==p.read_bytes(),'inventory not reviewed before application')
            for q in [p,s]:evidence[str(q.relative_to(ROOT))]=d.sha(q)
            proofs.update(plan['proofs'])
            archives.append(dict(name=name,original_bytes=status['unique_original_bytes'],archive_bytes=status['archive_bytes'],archive_sha256=status['archive_sha256']))
        d.require(all(d.sha(ROOT/p)==h for p,h in proofs.items()),'external evidence changed')
        fs=os.statvfs(ROOT)
        d.write_json(ROOT/'results/scalar-budget-cache-01/summary.json',dict(status='passed',archives=archives,
            original_bytes=sum(a['original_bytes'] for a in archives),archive_bytes=sum(a['archive_bytes'] for a in archives),
            external_hashes=len(proofs),proofs=proofs,evidence=evidence,inventory_commit='4df362f',
            observed_free_bytes=fs.f_bavail*fs.f_frsize,all_processes_terminal=True,processes_signaled=0,
            note='Terminal verify batch decoded every archive. Sources, executed artifacts, logs and tools preserved.'))
        print('Sixteen archives closed; external hashes:',len(proofs))


if __name__=='__main__':main()
