import hashlib,json,math,statistics,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
sys.path.insert(0,str(ROOT/'benchmarks/experiments/session-runtime-composition-parser-guards'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import require_space,write_json as write
from accounting import ratios,account
RUN='session-parser-control-variation-01'
HISTORY='session-runtime-composition-parser-incremental-01'
def read(p):return json.loads(p.read_text())
def derive():
    frozen={}
    def bind(p,h=None):
        digest=sha(p)
        if h is not None:assert digest==h,p
        frozen[str(p.relative_to(ROOT))]=digest;return read(p)
    out=ROOT/'results'/HISTORY;c=bind(out/'closure.json');assert c['status']=='closed' and c['all_hashes_verified']
    s=bind(out/'summary.json',c['summary_sha256']);t=bind(out/'terminal.json',c['terminal_sha256'])
    assert s['status']=='passed' and t['status']=='finished' and t['returncode']==0 and t['owner']==t['cwd']==str(ROOT)
    stage=ROOT/s['raw'];plan=bind(stage/'plan.json',s['plan_sha256'])
    records=bind(stage/'records.json',s['records_sha256']);sessions=bind(stage/'sessions.json',s['sessions_sha256'])
    assert ratios(records,sessions)==s['measurement'] and s['measurement']['verdict']=='unmeasurable' and not s['measurement']['gate_passed']
    for path in ['scripts/interpreter.py','benchmarks/experiments/session-runtime-composition-parser-guards/accounting.py']:
        h=sha(ROOT/path);assert h==plan['frozen'][path]['sha256'];frozen[path]=h
    launcher=(ROOT/'scripts/interpreter.py').read_text()
    assert "timings['build_to_ready_seconds']=time.perf_counter()-started" in launcher
    assert "timings['execution_seconds']=time.perf_counter()-stage" in launcher
    charged,_=account(records,sessions);pairs=[];work={k:[] for k in ['baseline','duplicate','candidate','session-fresh']}
    for cycle in range(3):
        for state in range(1,6):
            selected={r['mode']:r for r in charged if r['cycle']==cycle and r['state']==state};assert len(selected)==5
            assert len({r['source_sha256'] for r in selected.values()})==1
            assert len({r['artifact']['sha256'] for m,r in selected.items() if m!='native'})==1
            intervals={}
            for mode in work:
                r=selected[mode];j=bind(stage/(str(r['index'])+'-suite.json'),r['suite_sha256'])
                assert len(j['tests'])==j['passed']==114 and j['failed']==0
                row=dict(command_wall_seconds=r['accounted_wall_seconds'],command_cpu_seconds=r['accounted_cpu_seconds'],
                    build_to_ready_seconds=r['launch']['build_to_ready_seconds'],execution_seconds=r['launch']['execution_seconds'],
                    guest_test_work_seconds=sum(t['seconds'] for t in j['tests']),longest_test_seconds=max(t['seconds'] for t in j['tests']),
                    jit_compile_work_seconds=sum(t['jit_compile_ns'] for t in j['tests'])/1e9)
                row['outer_residual_seconds']=row['command_wall_seconds']-row['build_to_ready_seconds']-row['execution_seconds']
                assert row['outer_residual_seconds']>=0
                if mode in ['candidate','session-fresh']:
                    row['preparation_work_seconds']=sum(w['preparation_ns'] for w in j['worker_records'])/1e9
                    row['template_hits']=sum((w['templates'] or {}).get('hits',0) for w in j['worker_records'])
                work[mode].append(row);intervals[mode]=row
            a,b=intervals['baseline'],intervals['duplicate']
            delta={k:b[k]-a[k] for k in a}
            assert math.isclose(delta['command_wall_seconds'],sum(delta[k] for k in ['build_to_ready_seconds','execution_seconds','outer_residual_seconds']),abs_tol=1e-12)
            old=next(p for p in s['measurement']['pairs'] if p['cycle']==cycle and p['state']==state)
            ratio={metric:b['command_'+metric]/a['command_'+metric] for metric in ['wall_seconds','cpu_seconds']}
            assert all(ratio[k]==old[k]['aa'] for k in ratio)
            pairs.append(dict(cycle=cycle,state=state,aa=ratio,baseline=a,duplicate=b,duplicate_minus_baseline=delta,
                compiler_substage_seconds={m:selected[m]['stages'] for m in ['baseline','duplicate']}))
    medians={mode:{key:statistics.median(r[key] for r in rows) for key in rows[0]} for mode,rows in work.items()}
    ranked=sorted(pairs,key=lambda r:abs(r['aa']['wall_seconds']-1),reverse=True)
    assert abs(ranked[0]['aa']['wall_seconds']-1)==s['measurement']['medians']['wall_seconds']['aa_envelope']
    return dict(pairs=pairs,largest_wall_variation=ranked[0],descriptive_medians=medians,original_measurement=s['measurement'],
        gate_unchanged=True,all_pairs_retained=True,compiler_substages_are_overlapping=True,host_cause_inferred=False),frozen
def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,12)
        assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=ROOT).strip()
        revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip();d,frozen=derive()
        for p in [*Path(__file__).parent.glob('*.py'),*Path(__file__).parent.glob('*.md'),ROOT/'scripts/workflow_io.py',ROOT/'scripts/compare_saved_runtime.py']:
            frozen[str(p.relative_to(ROOT))]=sha(p)
        raw=ROOT/'.work'/RUN;raw.mkdir(exist_ok=False);write(raw/'derived.json',d)
        write(raw/'plan.json',dict(owner=str(ROOT),source_revision=revision,frozen=frozen,controller_command=[sys.executable,*sys.orig_argv[1:]],new_compiler_or_guest_commands=0,new_timing_samples=0))
        assert all(sha(ROOT/p)==h for p,h in frozen.items())
        out=ROOT/'results'/RUN;out.mkdir(exist_ok=False)
        write(out/'summary.json',dict(status='passed',source_revision=revision,raw=str(raw.relative_to(ROOT)),aa_pairs=15,suite_reports=60,
            largest_wall_variation=d['largest_wall_variation'],descriptive_medians=d['descriptive_medians'],original_gate_unchanged=True,
            original_verdict='unmeasurable',new_compiler_or_guest_commands=0,new_timing_samples=0,host_cause_inferred=False,
            plan_sha256=sha(raw/'plan.json'),derived_sha256=sha(raw/'derived.json')))
        print('All15 A/A pairs retained; original unmeasurable gate reproduced')
if __name__=='__main__':main()
