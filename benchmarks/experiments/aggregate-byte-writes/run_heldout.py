#!/usr/bin/env python3
"""One ordered, admitted real held-out workflow for the isolated compiler."""
import argparse
import fcntl
import os
from pathlib import Path
import subprocess
import sys
import time
from build_relocation import ROOT,HERE,PARENT,read,write,sha,require,installed_tools
from check_comparison import expected_tools
from heldout_controls import ORDER,case,assess
from heldout_space import estimate
from workflow_space import admit

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--case',choices=ORDER,required=True)
    args=parser.parse_args();label=args.case;c=case(label);run='aggregate-relocation-heldout-01-'+label
    work=ROOT/'.work'/run;work.mkdir(exist_ok=False)
    status=dict(status='preflight',pid=os.getpid(),parent_pid=os.getppid(),started_at=time.time());write(work/'status.json',status)
    try:
        with (ROOT/'.work/benchmark.lock').open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            primary=read(ROOT/'results/aggregate-relocation-e2e-01/summary.json')
            require(primary['primary_performance_gates_passed'],'primary gate failed')
            for name,count in [('native',47004),('tls',245)]:
                r=read(ROOT/'results'/('aggregate-relocation-'+name+'-01')/'summary.json')
                require(r['status']=='passed' and r['commands']==count,'broad '+name+' qualification incomplete')
            r=read(ROOT/'results/aggregate-relocation-fre-01/summary.json')
            require(r['status']=='passed' and r['counts']=={'passed':382,'ignored':7} and not r['outcome_changes'] and
                r['fresh_native_controls']==382,'fre outcome coverage incomplete')
            q=read(ROOT/'results/aggregate-relocation-heldout-controls-01/summary.json')
            require(len(q['actual_reports'])==9 and len(q['rejected'])==105 and q['status']=='passed','heldout verifier unqualified')
            require(all(sha(ROOT/p)==h for p,h in q['evidence'].items()),'qualified heldout verifier changed')
            q2=read(ROOT/'results/aggregate-relocation-heldout-admission-01/summary.json')
            require(q2['status']=='passed' and all(sha(ROOT/p)==h for p,h in q2['sources'].items()),'case admission/evaluator unqualified')
            if ORDER.index(label):
                previous=ROOT/'.work'/('aggregate-relocation-heldout-01-'+ORDER[ORDER.index(label)-1])/'status.json'
                require(read(previous)['status']=='finished','previous fixed case not terminal')
            tools=expected_tools()
            for mode,t in tools.items():
                directory,_=installed_tools(t['tool_key'])
                for name,key in [('rust-interp-vm','vm_sha256'),('rust-interp-mir-export','exporter_sha256'),('rust-interp-rustc-wrapper','wrapper_sha256')]:
                    require(sha(directory/name)==t[key],'immutable tool changed')
            needed,bound=estimate(label);fs=os.statvfs(ROOT);free=fs.f_bavail*fs.f_frsize
            admission=dict(label=label,checked_at=time.time(),observed_free_bytes=free,estimate=needed,passed=admit(free,needed),references=bound)
            write(work/'admission.json',admission);require(admission['passed'],'space admission rejected; no workflow started')
            command=[sys.executable,str(ROOT/'scripts/bench_e2e_workflow.py'),'--run-id',run,'--project',c['project'],'--workflow',c['workflow'],
                '--cycles','3','--jobs','4','--native-jobs','18','--native-profile','o0-incremental','--native-test-threads','default',
                '--check-floor','--minimum-free-gib','8','--candidate-tool-key',tools['candidate']['tool_key'],'--baseline-tool-key',PARENT,
                '--comparison-engine','jit','--candidate-jit-resumable-calls','--candidate-jit-persistent-registers',
                '--baseline-jit-resumable-calls','--baseline-jit-persistent-registers',*c['flags']]
            paths=[HERE/n for n in ['run_heldout.py','heldout_controls.py','heldout_space.py','check_heldouts.py','verify_heldouts.py',
                'check_comparison.py','QUALIFICATION-NEXT.md']]
            paths += [ROOT/'scripts'/n for n in ['bench_e2e_workflow.py','interpreter.py','workflow_cases.py','workflow_case_file.py',
                'workflow_controls.py','workflow_measurements.py','workflow_io.py','std_mir.py','workflow_jobs.py','workflow_space.py']]
            paths += [ROOT/'results'/n/'summary.json' for n in ['aggregate-relocation-e2e-01','aggregate-relocation-native-01',
                'aggregate-relocation-tls-01','aggregate-relocation-fre-01','aggregate-relocation-heldout-controls-01','aggregate-relocation-heldout-admission-01']]
            paths += [ROOT/'benchmarks/workflow-corpus.json']
            frozen={**bound,**{str(p.relative_to(ROOT)):sha(p) for p in paths}}
            write(work/'plan.json',dict(command=command,frozen=frozen,expected_tools=tools,case=c,admission=admission,
                source_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()))
        require(time.time()-admission['checked_at']<60,'space admission expired')
        with (work/'command.log').open('x') as log:
            child=subprocess.Popen(command,cwd=ROOT,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT)
            status.update(status='running',child_pid=child.pid,command=command,child_started_at=time.time(),
                child_identity=subprocess.check_output(['ps','-p',str(child.pid),'-o','pid,ppid,lstart,tty,command'],text=True))
            write(work/'status.json',status);code=child.wait()
        status.update(child_returncode=code,child_finished_at=time.time());write(work/'status.json',status)
        require(code==0,'heldout workflow failed; retain original history')
        with (ROOT/'.work/benchmark.lock').open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            require(all(sha(ROOT/p)==h for p,h in frozen.items()),'frozen heldout inputs changed')
            path=ROOT/'results'/run/'summary.json';r=read(path);result=assess(r,c)
            result.update(label=label,expected_tools=tools,evidence={**frozen,str(path.relative_to(ROOT)):sha(path)})
            write(path.with_name('relocation-assessment.json'),result)
            path.with_name('relocation-assessment.md').write_text(f"# {label}: aggregate relocation held-out\n\n"
                f"Gate {'passes' if result['passed'] else 'fails'}: paired wall {(result['wall_ratio']-1)*100:+.2f}%, CPU {(result['cpu_ratio']-1)*100:+.2f}%. "
                '63 primary commands, 21 checks, 15 real-edit pairs and 42 artifact hashes verify. '
                'Original assertions, wrong edits, source restoration and independent compiler/runtime controls are retained. '
                'Artifacts differ across the compiler change; semantic equivalence is not formally proven.\n')
        status.update(status='finished',passed=result['passed'],finished_at=time.time());write(work/'status.json',status)
        print({k:result[k] for k in ['label','passed','wall_ratio','cpu_ratio','median_seconds']})
    except BaseException as error:
        status.update(status='failed',error=repr(error),finished_at=time.time());write(work/'status.json',status);raise

if __name__=='__main__':main()
