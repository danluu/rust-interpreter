"""Preserve terminal success or failure receipts for this diagnostic experiment."""
import argparse
import fcntl
import re
from run import ROOT, read, write, sha, require


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    run = parser.parse_args().run_id
    require(re.fullmatch(r'scalar-boundary-admission-[0-9]{2}', run), 'unexpected run')
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        supervisor = ROOT/'.work/experiments'/run
        work = ROOT/'.work'/run
        s, c = read(supervisor/'status.json'), read(work/'status.json')
        require(s['status']=='finished' and c['status'] in ['finished','failed'] and
            s['child_pid']==c['pid'] and s['supervisor_pid']==c['parent_pid'], 'process chain not terminal')
        require(sha(supervisor/'plan.json')==s['plan_sha256'] and
            sha(supervisor/'command.log')==s['log_sha256'], 'supervisor evidence changed')
        if c['status']=='finished': require(s['returncode']==c['returncode']==0, 'success status differs')
        else: require(s['returncode']!=0, 'failure status differs')
        paths = [p for directory in [supervisor,work] for p in directory.iterdir() if p.is_file()]
        commands = read(work/'commands.json') if (work/'commands.json').exists() else []
        for command in commands:
            if 'files' in command:
                require(all(sha(ROOT/p)==h for p,h in command['files'].items()), 'command evidence changed')
        if (work/'provenance.json').exists():
            proof=read(work/'provenance.json')
            require(all(sha(ROOT/proof['source']/p)==h for p,h in proof['copied_inputs'].items()), 'isolated source changed')
        out = ROOT/'results'/run
        out.mkdir(exist_ok=True)
        if not (out/'summary.json').exists():
            write(out/'summary.json',dict(status='failed',error=c.get('error'),commands=commands,
                production_change=False,performance_measurement=False))
        paths.append(out/'summary.json')
        require(not (out/'execution.json').exists(), 'receipt already recorded')
        write(out/'execution.json',dict(supervisor=s,controller=c,all_processes_terminal=True,
            evidence={str(p.relative_to(ROOT)):sha(p) for p in paths}))
        print(dict(run=run,status=c['status'],evidence_files=len(paths)))


if __name__=='__main__': main()
