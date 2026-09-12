"""Preserve five completed scalar experiments' debug Cargo directories."""
import argparse
import fcntl
import os
from pathlib import Path
import subprocess
import sys
import time
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path.insert(0,str(HERE.parent/'published-build-cache'))
import archive as driver
BASE_SOURCES=driver.sources
CATALOG=driver.read(HERE/'catalog.json')


def evidence(run):
    driver.require(run in CATALOG,'uncatalogued diagnostic cache')
    item=CATALOG[run];proofs={}
    def bind(p,h=None):
        driver.require(p.resolve(strict=True)==p and p.is_file(),'noncanonical evidence')
        digest=driver.sha(p);driver.require(h is None or digest==h,'evidence changed: '+str(p))
        proofs[str(p.relative_to(ROOT))]=digest
        return driver.read(p) if p.suffix=='.json' else None
    report=bind(ROOT/'results'/run/'summary.json',item['summary_sha256'])
    receipt=bind(ROOT/'results'/run/'execution.json',item['execution_sha256'])
    s,c=receipt['supervisor'],receipt['controller']
    driver.require(receipt['all_processes_terminal'] and s['status']=='finished' and c['status'] in ['finished','failed']
        and s['owner']==s['cwd']==str(ROOT) and s['command']==item['command']
        and s['child_pid']==c['pid'] and s['supervisor_pid']==c['parent_pid']
        and s['finished_at']>=c['finished_at'],'ownership or terminal chain differs')
    driver.require((s['returncode']==0)==(report['status']=='passed'),'terminal outcome differs')
    for p,h in receipt['evidence'].items():bind(ROOT/p,h)
    work=ROOT/'.work'/run;parent=ROOT/'.work/diagnostic-builds'/run;target=parent/'debug'
    proof=bind(work/'provenance.json')
    for p,h in proof['copied_inputs'].items():bind(ROOT/proof['source']/p,h)
    for p,h in proof['root_frozen'].items():bind(ROOT/p,h)
    for p,h in report.get('frozen',{}).items():bind(ROOT/p,h)
    commands=driver.read(work/'commands.json')
    debug=[c for c in commands if c['label']=='debug'];driver.require(len(debug)==1,'debug command missing')
    argv=debug[0]['command'];driver.require(argv[:4]==['cargo','+nightly-2026-09-08','test','--workspace']
        and argv.count('--target-dir')==1 and argv[argv.index('--target-dir')+1]==str(parent)
        and argv[argv.index('--manifest-path')+1]==str(ROOT/proof['source']/'Cargo.toml'),'debug target ownership differs')
    driver.require(target.resolve(strict=True)==target and all(target not in (ROOT/p).parents for p in proofs),
        'retirement target contains evidence or is noncanonical')
    pids=[s['supervisor_pid'],c['pid'],*[row['pid'] for row in commands]]
    observed=subprocess.run(['ps','-p',','.join(map(str,pids)),'-o','pid,ppid,lstart,tty,command'],text=True,capture_output=True)
    driver.require(observed.returncode in [0,1] and not observed.stderr and
        all(run not in line for line in observed.stdout.splitlines()[1:]),'owned process still live')
    return target,proofs


def sources():
    return {**BASE_SOURCES(),**{str(p.relative_to(ROOT)):driver.sha(p) for p in [Path(__file__),HERE/'catalog.json']}}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--action',choices=['prepare','apply','verify'],required=True)
    action=parser.parse_args().action
    work=ROOT/'.work/scalar-debug-cache-01'/action;work.mkdir(parents=True,exist_ok=False)
    status=dict(status='starting',pid=os.getpid(),parent_pid=os.getppid(),started_at=time.time(),action=action)
    driver.write_json(work/'status.json',status)
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        driver.evidence=evidence;driver.sources=sources
        records=[]
        try:
            for run in CATALOG:
                name='scalar-debug-'+run+'-01';status.update(status='running',run=run);driver.write_json(work/'status.json',status)
                if action=='prepare':driver.prepare(run,name)
                elif action=='apply':driver.apply(name)
                else:
                    archive,plan,s,target=driver.load(name)
                    driver.require(s['status']=='completed' and not list(target.iterdir()),'retirement incomplete')
                    driver.require(driver.sha(archive/'cache.zip')==s['archive_sha256'],'archive changed')
                    driver.archive.verify_archive(archive/'cache.zip',plan['manifest'])
                records.append(dict(run=run,name=name,action=action,finished_at=time.time()))
                driver.write_json(work/'records.json',records)
            status.update(status='finished',returncode=0,finished_at=time.time());driver.write_json(work/'status.json',status)
        except BaseException as error:
            status.update(status='failed',error=repr(error),finished_at=time.time());driver.write_json(work/'status.json',status);raise


if __name__=='__main__':main()
