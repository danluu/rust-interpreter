#!/usr/bin/env python3
"""One preregistered six-pair rejection screen after local-cache correctness."""
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
import compare_saved_runtime as compare
from interpreter import installed_tools
from workflow_io import require_space,write_json as write


def main():
    run='jit-region-cache-screen-01'
    control_path=ROOT/'results/jit-register-width-build-02/summary.json'
    build_path=ROOT/'results/jit-region-cache-build-01/summary.json'
    smoke_path=ROOT/'results/jit-region-cache-smoke-02/summary.json'
    control=json.loads(control_path.read_text());build=json.loads(build_path.read_text());smoke=json.loads(smoke_path.read_text())
    assert control['status']==build['status']==smoke['status']=='passed'
    assert build['tests']['test-debug']==build['tests']['test-release']==dict(passed=339,ignored=1)
    assert smoke['commands']==8 and smoke['baseline_key']==control['tool_key'] and smoke['candidate_key']==build['tool_key']
    baseline,_=installed_tools(control['tool_key']);candidate,key=installed_tools(build['tool_key'])
    manifest=ROOT/'.work/jit-merged-token-01-inputs/manifest.json'
    qualification=ROOT/'results/fixed-frame-clear-entropy-check-01/summary.json'
    original=ROOT/'results/fixed-frame-clear-entropy-token-01/summary.json'
    expected=json.loads(original.read_text());cases=json.loads(manifest.read_text())
    assert len(cases)==1 and cases[0]['artifact_sha256']==expected['artifact_sha256']
    paths=[Path(__file__),Path(__file__).with_name('PLAN.md'),control_path,build_path,smoke_path,
           manifest,qualification,original,ROOT/'scripts/compare_saved_runtime.py',ROOT/'scripts/workflow_io.py']
    frozen={str(p.relative_to(ROOT)):compare.sha(p) for p in paths}
    old_acquire,old_popen,old_argv=compare.acquire_lock,compare.subprocess.Popen,sys.argv
    def acquire(lock,seconds):
        old_acquire(lock,seconds);require_space(ROOT,8)
    def popen(command,*args,**kwargs):
        require_space(ROOT,8)
        assert command[0] in [str(baseline/'rust-interp-vm'),str(candidate/'rust-interp-vm')]
        return old_popen(command,*args,**kwargs)
    compare.acquire_lock=acquire;compare.subprocess.Popen=popen
    sys.argv=[str(ROOT/'scripts/compare_saved_runtime.py'),'--baseline',str(baseline/'rust-interp-vm'),
        '--candidate',str(candidate/'rust-interp-vm'),'--manifest',str(manifest),'--output',str(ROOT/'.work'/run),
        '--lock',str(ROOT/'.work/benchmark.lock'),'--lock-wait-seconds','45','--repetitions','6','--engines','jit',
        '--entropy-qualification',str(qualification)]
    try:compare.main()
    finally:compare.acquire_lock=old_acquire;compare.subprocess.Popen=old_popen;sys.argv=old_argv
    assert all(compare.sha(ROOT/p)==h for p,h in frozen.items())
    work=ROOT/'.work'/run;summary=json.loads((work/'summary.json').read_text())
    assert summary['status']=='passed' and summary['commands']==14
    stages=[]
    for line in (work/'commands.jsonl').read_text().splitlines():
        row=json.loads(line);counts=expected['streams'][row['entropy']['stream']]['values']
        assert all(row['statistics'].get(k)==v for k,v in counts.items())
        assert row['statistics']['jit_declined_functions']==0
        stages.append(dict(mode=row['mode'],repetition=row['repetition'],statistics=row['statistics']))
    row=summary['rows'][0];wall=row['seconds']['median_paired_percent'];cpu=row['cpu_seconds']['median_paired_percent']
    passed=wall<=-10 and cpu<=0
    summary.update(frozen=frozen,baseline_key=control['tool_key'],candidate_key=key,raw=str(work.relative_to(ROOT)),
        runtime_screen_passed=passed,runtime_wall_percent_gate=-10,cpu_percent_gate=0,
        decision='Proceed to real five-edit build/test comparisons' if passed else 'Park this candidate; no retiming',
        qualified_entropy_counters_unchanged=True,jit_declines=0,whole_command_measurement=False)
    write(work/'statistics.json',stages)
    result=ROOT/'results'/run;result.mkdir(exist_ok=False);write(result/'summary.json',summary)
    print(summary['decision'],flush=True)


if __name__=='__main__':main()
