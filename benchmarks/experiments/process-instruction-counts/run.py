#!/usr/bin/env python3
"""Count retired instructions of owned, naturally exited test processes."""
import json
import os
from pathlib import Path
import re
import statistics
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from compare_saved_runtime import acquire_lock, sha
from workflow_io import capture, require_space, write_json as write

RUN = 'process-instruction-counts-01'
NAME = 'token_phrase::tests::exhaustive_small_byte_semantics_match_pinned_regex'
KEY = '49746a2218dbfdccacac0031f47e7a13b0440489c226979ff3374f6f899e09f9'


def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock, 45)
        require_space(ROOT, 3)
        probe_path = ROOT/'.work/retired-instruction-probe-01/plan.json'
        probe = json.loads(probe_path.read_text())
        assert probe['owner'] == str(ROOT) and probe['test'] == NAME
        native = Path(probe['command'][probe['command'].index('--')+1])
        assert sha(native) == probe['frozen'][str(native)]
        build_path = ROOT/'results/call-protocol-main-build-03/summary.json'
        build = json.loads(build_path.read_text())
        assert build['status'] == 'passed' and build['tool_key'] == KEY
        vm = ROOT/'.work/interpreter-tools'/KEY/'rust-interp-vm'
        assert sha(vm) == build['binaries']['rust-interp-vm']
        rbc = ROOT/'.work/filtered-workflow-token-02/6-automatic.rbc'
        catalog = rbc.with_suffix('.rbc.entries.json')
        assert sha(rbc) == '7aee80945e3329774159cb147e58376974b5f50f6e08d68bc985c07c484ab542'
        assert sha(catalog) == 'd3ef3700aae35ea72d22cf53bf4adc48775fa630a7cafacb559169c755f30913'
        selected, = [e for e in json.loads(catalog.read_text())['entries'] if e['name'] == NAME]
        qualification = ROOT/'results/call-protocol-main-qualification-01/summary.json'
        proof = json.loads(qualification.read_text())
        assert proof['status'] == 'passed' and proof['tool_key'] == KEY and proof['exact_instructions_memory_and_entropy']
        base = Path(__file__).parent
        frozen = {str(p):sha(p) for p in [Path(__file__),base/'launch.c',base/'PLAN.md',probe_path,
            build_path,qualification,native,vm,rbc,catalog,ROOT/'scripts/workflow_io.py',ROOT/'scripts/compare_saved_runtime.py']}
        env = {k:v for k,v in os.environ.items() if not k.startswith(('RUST_INTERP_','RUSTDEV_'))}
        assert not any(k.startswith('DYLD_') for k in env)
        env.pop('RUST_TEST_THREADS', None)
        work = ROOT/'.work'/RUN
        work.mkdir(exist_ok=False)
        commands = {
            'native': [str(native),'--exact',NAME,'--test-threads=1'],
            'jit': [str(vm),'--engine','jit','--jit-resumable-calls','--jit-persistent-registers',
                '--select-test',NAME,'--suite-catalog',str(catalog),'--instruction-limit','100000000000',
                '--allocation-limit','150000',str(rbc)]}
        write(work/'plan.json',dict(owner=str(ROOT),frozen=frozen,commands=commands,test=NAME,
            pairs=3,scope='whole target process lifetime; excludes parent launcher; no Cargo timing',
            source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()))
        launcher = work/'launch'
        command = ['xcrun','clang','-std=c11','-O2','-Wall','-Wextra','-Werror',str(base/'launch.c'),'-o',str(launcher)]
        child,out,err = capture(command,cwd=ROOT,env=env,receipt_path=work/'active.json',receipt=dict(phase='compile'))
        (work/'compile.stdout').write_text(out);(work/'compile.stderr').write_text(err)
        write(work/'compile.json',dict(command=command,pid=child.pid,returncode=child.returncode))
        assert child.returncode == 0, err
        frozen[str(launcher)] = sha(launcher)
        write(work/'frozen.json',frozen)
        rows = []

        def execute(label, command, expected_exit=0):
            require_space(ROOT, 3)
            counts,identity,stdout,stderr = [work/(label+'.'+suffix) for suffix in ['json','identity.json','stdout','stderr']]
            full = [str(launcher),str(counts),str(identity),str(stdout),str(stderr),'--',*command]
            started = time.perf_counter()
            child,out,err = capture(full,cwd=ROOT,env=env,receipt_path=work/'active.json',receipt=dict(label=label))
            row = dict(label=label,command=command,launcher_pid=child.pid,launcher_returncode=child.returncode,
                launcher_seconds=time.perf_counter()-started,launcher_stdout=out,launcher_stderr=err)
            if counts.exists() and counts.stat().st_size:
                row['counts'] = json.loads(counts.read_text())
            rows.append(row);write(work/'records.json',rows)
            assert child.returncode == 0, row
            c = row['counts']; owned = json.loads(identity.read_text())
            assert c['parent_pid'] == child.pid == owned['parent_pid']
            assert c['pid'] == c['waitid_pid'] == c['reaped_pid'] == owned['pid']
            assert not any(c[k] for k in ['wait_error','query_error','second_query_error','signal'])
            assert c['exit_code'] == c['waitid_status'] == expected_exit
            assert c['stable_after_exit'] and 0 < c['start_abstime'] < c['exit_abstime']
            assert c['instructions'] > 0 and c['cycles'] > 0
            assert all(sha(p)==h for p,h in frozen.items())
            row['evidence'] = {p.name:sha(p) for p in [counts,identity,stdout,stderr]}
            print(label,c['instructions'],c['cycles'],flush=True)
            return row,stdout.read_text(),stderr.read_text()

        small,_,_ = execute('probe-small',[str(launcher),'--spin','200000'])
        large,_,_ = execute('probe-large',[str(launcher),'--spin','2000000'])
        execute('probe-exit',[str(launcher),'--exit-seven'],7)
        assert large['counts']['instructions'] > small['counts']['instructions']
        pairs = []
        for pair in range(3):
            pair_rows = {}
            for mode in (['native','jit'] if pair%2 == 0 else ['jit','native']):
                row,out,err = execute(str(pair)+'-'+mode,commands[mode])
                row.update(pair=pair,mode=mode)
                if mode == 'native':
                    assert 'test '+NAME+' ... ok' in out and 'test result: ok. 1 passed;' in out
                else:
                    assert out == '0\n'
                    match, = re.findall(r'^rust-interp-test-selection: (.+)$',err,re.M)
                    selection = json.loads(match)
                    assert selection['artifact_sha256'] == sha(rbc) and selection['catalog_sha256'] == sha(catalog)
                    assert selection['name'] == NAME and selection['function'] == selected['function']
                    row['selection'] = selection
                    logical, = re.findall(r'^instructions=(\d+) peak_guest_memory=(\d+)$',err,re.M)
                    row['logical_instructions'],row['peak_guest_memory'] = map(int,logical)
                pair_rows[mode] = row
                write(work/'records.json',rows)
            a,b = [pair_rows[m]['counts'] for m in ['native','jit']]
            pairs.append(dict(pair=pair,instruction_ratio=b['instructions']/a['instructions'],
                cycle_ratio=b['cycles']/a['cycles'],native_cycles_per_instruction=a['cycles']/a['instructions'],
                jit_cycles_per_instruction=b['cycles']/b['instructions']))
        write(work/'records.json',rows)
        result = dict(status='passed',target_commands=len(rows),diagnostic_pairs=3,pairs=pairs,
            median_instruction_ratio=statistics.median(p['instruction_ratio'] for p in pairs),
            median_cycle_ratio=statistics.median(p['cycle_ratio'] for p in pairs),
            whole_process_counts=True,pure_guest_counts=False,performance_adoption_measurement=False,
            ordinary_os_entropy=True,test=NAME,tool_key=KEY,raw=str(work.relative_to(ROOT)),
            records_sha256=sha(work/'records.json'),frozen_sha256=sha(work/'frozen.json'),
            limitation='Whole lifetime includes native libtest setup and custom decode/lowering/codegen. No per-phase hardware attribution, exact entropy equivalence, or Cargo timing.')
        destination = ROOT/'results'/RUN;destination.mkdir(exist_ok=False);write(destination/'summary.json',result)
        print(json.dumps(result),flush=True)


if __name__ == '__main__':main()
