"""Qualify the typed join and reconcile exact original profiles; no guest execution."""
import argparse
import collections
import fcntl
import os
from pathlib import Path
import re
import subprocess
import time
from build import ROOT, HERE, PARENT, environment, installed_tools, index, read, write, sha, require


def aggregate(report):
    groups={}
    for row in report['rows']:
        key=row['typed']['role']+':'+row['category']
        group=groups.setdefault(key,dict(rows=0,accesses=collections.Counter(),rejections=collections.Counter()))
        group['rows']+=1
        group['accesses'].update(row['accesses'])
        group['rejections'].update(row['typed']['rejections'])
    return groups


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id',required=True)
    args=parser.parse_args();run=args.run_id
    require(re.fullmatch(r'scalar-boundary-census-[0-9]{2}',run),'invalid run ID')
    work=ROOT/'.work'/run;work.mkdir(exist_ok=False)
    status=dict(status='preflight',pid=os.getpid(),parent_pid=os.getppid(),started_at=time.time())
    write(work/'status.json',status)
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        try:
            fs=os.statvfs(ROOT);require(fs.f_bavail*fs.f_frsize>=9*1024**3,'insufficient analysis-build space')
            tool=index('5b2330c');require(tool['tool_key']==PARENT,'integrated source differs')
            installed,_=installed_tools(PARENT)
            export_path=ROOT/'results/scalar-boundary-export-smoke-02/summary.json'
            export=read(export_path)
            require(export['status']=='passed' and export['source_unchanged'] and
                    all(c['bytecode_identical'] and c['original_assertions_pass'] for c in export['cases']),'exports not qualified')
            receipt_path=export_path.with_name('execution.json');receipt=read(receipt_path)
            require(receipt['all_processes_terminal'] and all(sha(ROOT/p)==h for p,h in receipt['evidence'].items()),'export execution changed')
            prior_path=ROOT/'results/budget-register-smoke-05/summary.json'
            prior=read(prior_path)
            commands_path=ROOT/'.work/budget-register-smoke-05/commands.json'
            recorded=read(commands_path);require(recorded==prior['commands'],'original command records differ')
            frozen={str(p.relative_to(ROOT)):sha(p) for p in
                [export_path,receipt_path,prior_path,commands_path,ROOT/'scripts/tool_source_index.py',ROOT/'scripts/interpreter.py']}
            for path,digest in tool['files'].items():
                if path.startswith('crates/bytecode/'):
                    require(sha(ROOT/path)==digest,'bytecode implementation changed');frozen[path]=digest
            frozen.update({str(p.relative_to(ROOT)):sha(p) for p in HERE.iterdir() if p.is_file()})
            inputs=[]
            for label,number in [('folded-literal-trie',1),('token-phrase',11)]:
                old=recorded[number];command=old['command']
                require(old['label']==label and old['mode']=='baseline' and old['profiled'] and old['returncode']==0
                    and Path(command[0])==installed/'rust-interp-vm','original profile invocation differs')
                for path,digest in old['files'].items():
                    require(sha(ROOT/path)==digest,'profile evidence changed');frozen[path]=digest
                artifact=Path(command[-1]);profile=Path(command[command.index('--profile')+1])
                require(sha(artifact)==prior['frozen'][str(artifact.relative_to(ROOT))],'original artifact changed')
                observed=next(c for c in export['cases'] if c['label']==label)
                inventory=ROOT/observed['inventory']
                require(sha(inventory)==observed['inventory_sha256'] and sha(artifact)==observed['artifact_sha256'],'observer/profile artifact differs')
                for p in [artifact,inventory,profile]:frozen[str(p.relative_to(ROOT))]=sha(p)
                stats={k:int(v) for k,v in re.findall(r'\b([a-z_]+)=(\d+)\b',(ROOT/f'.work/budget-register-smoke-05/{number}.stderr').read_text())}
                require(stats['jit_declined_functions']==0,'original JIT declines')
                inputs.append(dict(label=label,artifact=str(artifact),profile=str(profile),inventory=str(inventory),statistics=stats))
            def verify():
                require(all(sha(ROOT/p)==h for p,h in frozen.items()),'frozen analysis input changed')
            env=environment();commands=[]
            def execute(label,argv,destination=None):
                verify();fs=os.statvfs(ROOT);require(fs.f_bavail*fs.f_frsize>=8*1024**3,'eight-GiB floor rejected')
                log=destination or work/(label+'.log');error=work/(label+'.stderr')
                with log.open('x') as out,error.open('x') as err:
                    child=subprocess.Popen(argv,cwd=ROOT,env=env,stdin=subprocess.DEVNULL,stdout=out,stderr=err)
                    try:
                        status.update(status='running',child_pid=child.pid,command=argv,child_cwd=str(ROOT),
                            child_started_at=time.time(),child_identity=subprocess.check_output(['ps','-p',str(child.pid),'-o','pid,ppid,lstart,tty,command'],text=True))
                        write(work/'status.json',status)
                    finally:code=child.wait()
                commands.append(dict(label=label,command=argv,pid=child.pid,returncode=code,
                    files={str(p.relative_to(ROOT)):sha(p) for p in [log,error]}))
                write(work/'commands.json',commands);require(code==0,label+' failed');verify()
            cargo=['cargo','+nightly-2026-09-08']
            if not (HERE/'Cargo.lock').exists():
                execute('lockfile',cargo+['generate-lockfile','--offline','--manifest-path',str(HERE/'Cargo.toml')])
                frozen[str((HERE/'Cargo.lock').relative_to(ROOT))]=sha(HERE/'Cargo.lock')
            write(work/'plan.json',dict(frozen=frozen,inputs=inputs,source_commit=tool['commit'],tool_key=PARENT,
                observed_tool_key=export['tool_key'],new_guest_executions=0,performance_measurement=False))
            target=ROOT/'.work/diagnostic-builds'/run;require(not target.exists(),'analysis target already exists')
            flags=['--release','--locked','--offline','--jobs','2','--manifest-path',str(HERE/'Cargo.toml'),'--target-dir',str(target)]
            execute('tests',cargo+['test']+flags)
            require('test result: ok. 5 passed; 0 failed; 0 ignored;' in (work/'tests.log').read_text(),'analysis tests differ')
            execute('build',cargo+['build']+flags)
            binary=target/'release/scalar-boundary-census';frozen[str(binary.relative_to(ROOT))]=sha(binary)
            cases=[]
            for row in inputs:
                destination=work/(row['label']+'.json')
                execute(row['label'],[str(binary),row['artifact'],row['profile'],row['inventory'],str(row['statistics']['instructions'])],destination)
                report=read(destination);totals=report['totals'];stats=row['statistics']
                require(totals['native_instructions']==stats['jit_instructions'] and totals['native_direct_calls']==stats['jit_resumable_calls']
                    and totals['native_returns']==stats['jit_resumable_returns'],'native profile accounting differs')
                if row['label']=='token-phrase':require(totals['random_events']>0,'original entropy missing')
                cases.append(dict(label=row['label'],report=str(destination.relative_to(ROOT)),report_sha256=sha(destination),
                    totals=totals,boundary=report['boundary'],coverage=report['coverage'],groups=aggregate(report)))
            verify()
            result=dict(status='passed',tool_key=PARENT,observed_tool_key=export['tool_key'],tests_passed=5,
                cases=cases,frozen=frozen,commands=commands,new_guest_executions=0,performance_measurement=False,
                note='Original exact profiles and byte-identical observed artifacts. Counts are opportunities, not speedup predictions; unknown addresses/indirect callees remain explicit.')
            write(work/'summary.json',result);out=ROOT/'results'/run;out.mkdir(exist_ok=False);write(out/'summary.json',result)
            status.update(status='finished',returncode=0,finished_at=time.time());write(work/'status.json',status)
            print({c['label']:dict(instructions=c['totals']['instructions'],coverage=c['coverage']) for c in cases})
        except BaseException as error:
            status.update(status='failed',error=repr(error),finished_at=time.time());write(work/'status.json',status);raise


if __name__=='__main__':main()
