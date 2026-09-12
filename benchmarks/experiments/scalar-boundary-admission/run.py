"""Qualify exact scalar address admission, then weight the original workloads."""
import argparse
import collections
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path.insert(0,str(HERE.parent/'scalar-boundary-census'))
from build import read,write,sha,require,environment,index


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id',required=True)
    run=parser.parse_args().run_id
    require(re.fullmatch(r'scalar-boundary-admission-[0-9]{2}',run),'invalid run')
    work=ROOT/'.work'/run;work.mkdir(exist_ok=False)
    status=dict(status='preflight',pid=os.getpid(),parent_pid=os.getppid(),started_at=time.time())
    write(work/'status.json',status)
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        try:
            fs=os.statvfs(ROOT);require(fs.f_bavail*fs.f_frsize>=9*1024**3,'insufficient host-build allowance')
            source=index('5b2330c')
            require(source['tool_key']=='9637b0acb1d208524c3c8b446af64cfd5e2d0d3be75e1412a8df76750ce36223','wrong integrated source')
            for p,h in source['files'].items():require(sha(ROOT/p)==h,'integrated source changed')
            prior_path=ROOT/'results/scalar-boundary-census-01/summary.json';prior=read(prior_path)
            receipt=read(prior_path.with_name('execution.json'))
            require(prior['status']=='passed' and prior['tests_passed']==5 and receipt['all_processes_terminal'],'prior census incomplete')
            for p,h in prior['frozen'].items():require(sha(ROOT/p)==h,'prior census input changed')
            for p,h in receipt['evidence'].items():require(sha(ROOT/p)==h,'prior execution changed')
            old_plan=read(ROOT/'.work/scalar-boundary-census-01/plan.json')
            files=[p for p in HERE.iterdir() if p.is_file()]
            files += [prior_path,prior_path.with_name('execution.json'),ROOT/'.work/scalar-boundary-census-01/plan.json',
                HERE.parent/'scalar-boundary-census/profile.rs',HERE.parent/'scalar-boundary-census/build.py',
                ROOT/'scripts/tool_source_index.py',ROOT/'scripts/interpreter.py',ROOT/'scripts/verify_repeated_workflow.py']
            frozen={**source['files'],**{str(p.relative_to(ROOT)):sha(p) for p in files}}
            inputs=[]
            for case in prior['cases']:
                old=next(c for c in old_plan['inputs'] if c['label']==case['label'])
                report=ROOT/case['report'];require(sha(report)==case['report_sha256'],'prior raw census changed')
                inputs.append(dict(label=case['label'],artifact=old['artifact'],profile=old['profile'],prior=str(report)))
                for p in [report,Path(old['artifact']),Path(old['profile'])]:frozen[str(p.relative_to(ROOT))]=sha(p)
            write(work/'plan.json',dict(frozen=frozen,inputs=inputs,source_commit=source['commit'],tool_key=source['tool_key'],
                probe_bodies_executed=False,performance_measurement=False))
            def verify():require(all(sha(ROOT/p)==h for p,h in frozen.items()),'frozen admission input changed')
            commands=[];env=environment()
            def command(label,argv,destination=None):
                verify();fs=os.statvfs(ROOT);require(fs.f_bavail*fs.f_frsize>=8*1024**3,'eight-GiB floor rejected')
                out=destination or work/(label+'.log');err=work/(label+'.stderr')
                with out.open('x') as stdout,err.open('x') as stderr:
                    child=subprocess.Popen(argv,cwd=ROOT,env=env,stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr)
                    try:
                        status.update(status='running',child_pid=child.pid,command=argv,child_started_at=time.time(),child_cwd=str(ROOT),
                            child_identity=subprocess.check_output(['ps','-p',str(child.pid),'-o','pid,ppid,lstart,tty,command'],text=True))
                        write(work/'status.json',status)
                    finally:code=child.wait()
                commands.append(dict(label=label,command=argv,pid=child.pid,returncode=code,
                    files={str(p.relative_to(ROOT)):sha(p) for p in [out,err]}))
                write(work/'commands.json',commands);require(code==0,label+' failed');verify()
            target=ROOT/'.work/diagnostic-builds'/run;require(not target.exists(),'build target exists')
            cargo=['cargo','+nightly-2026-09-08'];flags=['--release','--locked','--offline','--jobs','2',
                '--manifest-path',str(HERE/'Cargo.toml'),'--target-dir',str(target)]
            command('tests',cargo+['test']+flags)
            tests=(work/'tests.log').read_text()
            require('test result: ok. 11 passed; 0 failed; 0 ignored;' in tests,'test qualification differs')
            names=re.findall(r'^test (\S+) \.\.\. ok$',tests,re.M)
            require(len(names)==11 and sum(n.startswith('transform::tests::') for n in names)==5
                and sum(n.startswith('transform::scalar_moves::tests::') for n in names)==3,'existing transform tests missing')
            command('build',cargo+['build']+flags)
            binary=target/'release/scalar-boundary-admission';frozen[str(binary.relative_to(ROOT))]=sha(binary)
            cases=[]
            for case in inputs:
                path=work/(case['label']+'.json')
                command(case['label'],[str(binary),case['artifact'],case['profile'],case['prior']],path)
                report=read(path);groups={}
                for row in report['rows']:
                    key=row['typed']['role']+':'+row['category']+':'+row['shape']['reason']
                    group=groups.setdefault(key,dict(rows=0,accesses=collections.Counter(),boundary=collections.Counter()))
                    group['rows']+=1;group['accesses'].update(row['accesses']);group['boundary'].update(row['boundary'])
                cases.append(dict(label=case['label'],report=str(path.relative_to(ROOT)),report_sha256=sha(path),
                    rows=len(report['rows']),admitted=sum(r['shape']['admitted'] for r in report['rows']),
                    totals=report['totals'],boundary=report['boundary'],groups=groups,probe_operations=report['probe_operations']))
            verify()
            result=dict(status='passed',tool_key=source['tool_key'],tests_passed=11,test_names=names,cases=cases,frozen=frozen,
                commands=commands,performance_measurement=False,probe_bodies_executed=False,new_original_workload_executions=0,
                note='Existing scalar transform address-use admission only; probes are discarded. Entry initialization/result publication still need an explicit scalar ABI.')
            write(work/'summary.json',result);out=ROOT/'results'/run;out.mkdir(exist_ok=False);write(out/'summary.json',result)
            status.update(status='finished',returncode=0,finished_at=time.time());write(work/'status.json',status)
            print({c['label']:dict(rows=c['rows'],admitted=c['admitted'],probe_operations=c['probe_operations']) for c in cases})
        except BaseException as error:
            status.update(status='failed',error=repr(error),finished_at=time.time());write(work/'status.json',status);raise


if __name__=='__main__':main()
