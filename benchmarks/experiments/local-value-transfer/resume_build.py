"""Retain the passed debug package tests; run only the unstarted release command."""
import json
import os
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write


def counts(out):
    groups=re.findall(r'test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored;',out)
    assert groups and all(int(f)==0 for _,f,_ in groups)
    total=dict(passed=sum(int(n) for n,_,_ in groups),ignored=sum(int(n) for _,_,n in groups))
    assert total==dict(passed=408,ignored=6),total
    assert len(re.findall(r'^test jit::local_memory::transfer_tests::.* \.\.\. ok$',out,re.M))==8
    return total


def main():
    run='local-value-transfer-build-continuation-01'
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,12)
        before=ROOT/'.work/local-value-transfer-build-01'
        terminal_path=ROOT/'.work/experiments/local-value-transfer-build-01/status.json'
        terminal=json.loads(terminal_path.read_text())
        assert terminal['status']=='finished' and terminal['returncode']==1
        assert terminal['owner']==str(ROOT) and terminal['child_pid']==37321
        assert sha(terminal_path.with_name('command.log'))==terminal['log_sha256']
        plan=json.loads((before/'plan.json').read_text());records=json.loads((before/'records.json').read_text())
        assert plan['owner']==str(ROOT) and len(records)==1
        first,=records
        assert first['label']=='debug' and first['returncode']==0
        assert first['command']==plan['commands'][0][1]
        for stream in ['stdout','stderr']:assert sha(before/('debug.'+stream))==first[stream+'_sha256']
        debug=counts((before/'debug.stdout').read_text())
        frozen=dict(plan['frozen'])
        for p in [Path(__file__),before/'plan.json',before/'records.json',before/'debug.stdout',
                  before/'debug.stderr',terminal_path,terminal_path.with_name('command.log')]:
            frozen[str(p.relative_to(ROOT))]=sha(p)
        assert all(sha(ROOT/p)==h for p,h in frozen.items())
        command=plan['commands'][1][1]
        assert plan['commands'][1][0]=='release' and '--release' in command
        work=ROOT/'.work'/run;work.mkdir(exist_ok=False)
        write(work/'plan.json',dict(owner=str(ROOT),frozen=frozen,command=command,retained_commands=1,
            new_commands=1,repeated_commands=0,correction='The bytecode package baseline has400 tests, not403; eight new tests give408. The original411 expectation included three exporter-main tests.',performance_measurement=False))
        env={k:v for k,v in os.environ.items() if not k.startswith(('RUST_INTERP_','RUSTDEV_','CARGO_PROFILE_'))
             and k not in ['RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','RUSTC','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER',
                           'CARGO_INCREMENTAL','CARGO_TARGET_DIR','CARGO_BUILD_TARGET','RUST_TEST_THREADS']}
        assert not any(k.startswith('DYLD_') for k in env)
        env.update(CARGO_TERM_COLOR='never',CARGO_INCREMENTAL='0',CARGO_PROFILE_DEV_DEBUG='0',
                   CARGO_PROFILE_TEST_DEBUG='0',CARGO_PROFILE_RELEASE_DEBUG='1',PYTHONDONTWRITEBYTECODE='1')
        require_space(ROOT,8)
        child,out,err=capture(command,cwd=ROOT,env=env,receipt_path=work/'active.json',receipt=dict(label='release'))
        (work/'release.stdout').write_text(out);(work/'release.stderr').write_text(err)
        row=dict(label='release',command=command,pid=child.pid,returncode=child.returncode,
            stdout_sha256=sha(work/'release.stdout'),stderr_sha256=sha(work/'release.stderr'))
        write(work/'records.json',[dict(first,retained_from=str(before.relative_to(ROOT))),row])
        assert child.returncode==0,(out+err)[-3000:]
        release=counts(out)
        assert all(sha(ROOT/p)==h for p,h in frozen.items())
        result=ROOT/'results'/run;result.mkdir(exist_ok=False)
        write(result/'summary.json',dict(status='passed',commands=2,retained_commands=1,new_commands=1,
            repeated_commands=0,tests=dict(debug=debug,release=release),transfer_tests=8,
            raw=str(work.relative_to(ROOT)),plan_sha256=sha(work/'plan.json'),records_sha256=sha(work/'records.json'),
            production_transfer_enabled=False,performance_measurement=False))
        print('PASS:408 bytecode tests/profile; retained debug, new release, no repeats',flush=True)


if __name__=='__main__':main()
