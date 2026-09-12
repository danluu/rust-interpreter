#!/usr/bin/env python3
"""Reconcile two existing original-artifact profiles with a typed Call census."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT/'scripts'))
from interpreter import installed_tools
from tool_source_index import index


def read(p): return json.loads(p.read_text())
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def require(ok, message):
    if not ok: raise RuntimeError(message)
def write(p, value):
    temporary = p.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, indent=2)+'\n'); temporary.replace(p)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    run = parser.parse_args().run_id
    require(re.fullmatch(r'whole-call-census-[0-9]{2}', run), 'unexpected census ID')
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        work = ROOT/'.work'/run; work.mkdir(exist_ok=False)
        out = ROOT/'results'/run; out.mkdir(exist_ok=False)
        status = dict(status='preflight', pid=os.getpid(), parent_pid=os.getppid(), started_at=time.time())
        write(work/'status.json', status)
        for p in HERE.iterdir():
            if p.is_file(): shutil.copy2(p, out/p.name)
        try:
            tool = index('5b2330c')
            require(tool['tool_key'] == '9637b0acb1d208524c3c8b446af64cfd5e2d0d3be75e1412a8df76750ce36223', 'source identity differs')
            installed, _ = installed_tools(tool['tool_key'])
            smoke_path = ROOT/'results/budget-register-smoke-05/summary.json'
            smoke = read(smoke_path)
            require(smoke['status'] == 'passed' and smoke['control_tool_key'] == tool['tool_key'], 'unqualified profile source')
            command_path = ROOT/'.work/budget-register-smoke-05/commands.json'
            prior = read(command_path)
            receipt_path = ROOT/'results/budget-register-smoke-05/execution.json'
            receipt = read(receipt_path)
            require(receipt['evidence'][str(smoke_path.relative_to(ROOT))] == sha(smoke_path)
                    and prior == smoke['commands'], 'smoke command receipt differs')
            source = {str(p.relative_to(ROOT)):sha(p) for p in HERE.iterdir() if p.is_file()}
            source[str((HERE.parent/'call-slot-census/tests.rs').relative_to(ROOT))]=sha(HERE.parent/'call-slot-census/tests.rs')
            source.update({p:h for p,h in tool['files'].items() if p.startswith('crates/bytecode/')})
            frozen = {**source, **{str(p.relative_to(ROOT)):sha(p) for p in
                [smoke_path, command_path, receipt_path, ROOT/'scripts/tool_source_index.py', ROOT/'scripts/interpreter.py', installed/'rust-interp-vm']}}
            inputs = []
            for label, number in [('folded-literal-trie',1),('token-phrase',11)]:
                row = prior[number]; command = row['command']
                require(row['label'] == label and row['mode'] == 'baseline' and row['profiled'] and
                    row['returncode'] == 0 and Path(command[0]) == installed/'rust-interp-vm' and
                    '--jit-resumable-calls' in command and '--jit-persistent-registers' in command,
                    'original control invocation differs')
                for path, digest in row['files'].items():
                    require(sha(ROOT/path) == digest, 'original profile evidence changed')
                    frozen[path] = digest
                artifact = Path(command[-1]); profile = Path(command[command.index('--profile')+1])
                relative = str(artifact.relative_to(ROOT))
                require(sha(artifact) == smoke['frozen'][relative], 'original artifact changed')
                frozen[relative] = sha(artifact)
                stderr = ROOT/f'.work/budget-register-smoke-05/{number}.stderr'
                stats = {k:int(v) for k,v in re.findall(r'\b([a-z_]+)=(\d+)\b',stderr.read_text())}
                require(stats['jit_declined_functions'] == 0, 'unexpected original JIT decline')
                require((ROOT/f'.work/budget-register-smoke-05/{number}.stdout').read_text().strip() == '0', 'original assertions did not pass')
                inputs.append(dict(label=label, artifact=str(artifact), profile=str(profile), statistics=stats, command_index=number))
            def verify():
                require(all(sha(ROOT/p) == h for p,h in frozen.items()), 'frozen census input changed')
            verify()
            target = ROOT/'.work/diagnostic-builds'/run
            require(not target.exists(), 'diagnostic target already exists')
            write(work/'plan.json', dict(tool_key=tool['tool_key'], source_commit=tool['commit'], frozen=frozen, inputs=inputs,
                source_snapshot=str(out.relative_to(ROOT)), new_guest_executions=0, performance_measurement=False))
            env = os.environ.copy()
            for name in list(env):
                if name.startswith(('RUST_INTERP_', 'RUSTDEV_', 'CARGO_PROFILE_')) or name in [
                    'RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','RUSTC','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER',
                    'CARGO_INCREMENTAL','CARGO_TARGET_DIR','CARGO_BUILD_TARGET']:
                    env.pop(name)
            env['CARGO_TERM_COLOR']='never'
            commands=[]
            def command(label, argv, destination=None):
                verify()
                fs=os.statvfs(ROOT); require(fs.f_bavail*fs.f_frsize >= 8*1024**3, 'eight-GiB floor rejected')
                log = destination or work/(label+'.log')
                with log.open('x') as stdout, (work/(label+'.stderr')).open('x') as stderr:
                    child=subprocess.Popen(argv,cwd=ROOT,env=env,stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr)
                    try:
                        status.update(status='running', child_pid=child.pid, command=argv, child_started_at=time.time())
                        write(work/'status.json',status)
                    finally: code=child.wait()
                commands.append(dict(label=label,command=argv,pid=child.pid,parent_pid=os.getpid(),returncode=code,
                    files={str(p.relative_to(ROOT)):sha(p) for p in [log,work/(label+'.stderr')]}))
                write(work/'commands.json',commands)
                require(code == 0, label+' failed')
                verify()
            cargo=['cargo','+nightly-2026-09-08']
            flags=['--release','--locked','--offline','--jobs','2','--manifest-path',str(HERE/'Cargo.toml'),'--target-dir',str(target)]
            command('tests',cargo+['test']+flags)
            require('test result: ok. 17 passed; 0 failed; 0 ignored;' in (work/'tests.log').read_text(), 'census test coverage differs')
            command('build',cargo+['build']+flags)
            binary=target/'release/whole-call-census'; frozen[str(binary.relative_to(ROOT))]=sha(binary)
            cases=[]
            for row in inputs:
                destination=out/(row['label']+'.json')
                command(row['label'],[str(binary),row['artifact'],row['profile'],str(row['statistics']['instructions'])],destination)
                output=read(destination)
                data=output['census']
                require(data['native_instructions'] == row['statistics']['jit_instructions'], 'native instruction accounting differs')
                require(data['totals']['direct']['native_calls'] == row['statistics']['jit_resumable_calls'], 'native Call accounting differs')
                require(data['native_returns'] == row['statistics']['jit_resumable_returns'], 'native Return accounting differs')
                if row['label']=='token-phrase': require(data['random_events'] > 0, 'original entropy path missing')
                cases.append(dict(label=row['label'],report=str(destination.relative_to(ROOT)),report_sha256=sha(destination),
                    **{k:v for k,v in data.items() if k != 'sites'},executed_call_sites=len(data['sites']), opportunities=output['opportunities'], placements=output['placements']))
            write(out/'summary.json',dict(status='passed',tool_key=tool['tool_key'],source_commit=tool['commit'],
                tests_passed=17,new_guest_executions=0,performance_measurement=False,cases=cases,frozen=frozen,commands=commands,
                limitation='Dynamic counts from unchanged artifacts are opportunities, not speedup estimates. Leaf eligibility excludes caller growth and placement guards; it does not simulate inlining. No transformed guest executes.'))
            status.update(status='finished',returncode=0,finished_at=time.time());write(work/'status.json',status)
            print(json.dumps(dict(status='passed',cases=[dict(label=c['label'],totals=c['totals'],declined_functions=len(c['declined_functions'])) for c in cases])),flush=True)
        except BaseException as error:
            status.update(status='failed',error=repr(error),finished_at=time.time());write(work/'status.json',status)
            write(out/'failure.json',status)
            raise


if __name__ == '__main__': main()
