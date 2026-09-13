"""Measure proof coverage on exact saved native calls and clearing sample PCs."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
sys.path.insert(0,str(ROOT/'benchmarks/experiments/native-call-cost-census'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import require_space,write_json as write
from summarize_owned_sample import parse_tree,self_samples
from analyze import call_index,attribute


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run-id',required=True);args=p.parse_args()
    assert re.fullmatch(r'frame-initialization-cfg-coverage-\d{2}',args.run_id)
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,12)
        build_path=ROOT/'results/frame-initialization-cfg-build-02/summary.json';build=json.loads(build_path.read_text())
        assert build['status']=='passed' and build['tests']=={'debug':8,'release':8} and build['oracle_cases_per_profile']==6400
        raw=ROOT/build['raw'];typed_path=raw/'typed.json';assert sha(typed_path)==build['typed_sha256']
        typed=json.loads(typed_path.read_text());functions=typed['functions'];assert len(functions)==build['functions']
        paths=[Path(__file__),Path(__file__).with_name('PLAN.md'),build_path,typed_path,
               ROOT/'benchmarks/experiments/native-call-cost-census/analyze.py',ROOT/'scripts/summarize_owned_sample.py',
               ROOT/'scripts/workflow_io.py',ROOT/'scripts/compare_saved_runtime.py']
        history=[]
        for name,expected_code in [('frame-initialization-cfg-build-01',1),('frame-initialization-cfg-build-02',0)]:
            result=ROOT/'results'/name;summary=json.loads((result/'summary.json').read_text());base=ROOT/summary['raw']
            terminal=json.loads((result/'terminal.json').read_text());outer=ROOT/'.work/experiments'/name
            assert terminal['status']=='finished' and terminal['returncode']==expected_code
            assert terminal['owner']==terminal['cwd']==str(ROOT)
            assert sha(outer/'status.json')==sha(result/'terminal.json')
            assert sha(outer/'plan.json')==terminal['plan_sha256'] and sha(outer/'command.log')==terminal['log_sha256']
            plan=json.loads((base/'plan.json').read_text());assert sha(base/'plan.json')==summary['plan_sha256']
            assert sha(base/'records.json')==summary['records_sha256']
            records=json.loads((base/'records.json').read_text())
            if expected_code:assert summary['tests_executed']==0 and len(records)==1 and records[0]['returncode']==101
            else:assert len(records)==4 and all(r['returncode']==0 for r in records)
            for row in records:
                for suffix in ['stdout','stderr']:
                    f=base/(row['label']+'.'+suffix);assert sha(f)==row[suffix+'_sha256'];paths.append(f)
            for file,digest in plan['frozen'].items():
                if file.startswith(('crates/','benchmarks/','scripts/','results/')):
                    spec=plan['source_revision']+':'+file
                    assert hashlib.sha256(subprocess.check_output(['git','show',spec],cwd=ROOT)).hexdigest()==digest
                    history.append(dict(path=file,sha256=digest,git_source=spec))
                else:assert sha(ROOT/file)==digest
            paths += [result/'summary.json',result/'terminal.json',base/'plan.json',base/'records.json',outer/'plan.json',outer/'command.log']
        previous_path=ROOT/'results/native-call-cost-census-01/summary.json';previous=json.loads(previous_path.read_text())
        assert previous['status']=='passed' and previous['all_frozen_inputs_verified']
        previous_plan=ROOT/previous['raw']/'plan.json';assert sha(previous_plan)==previous['plan_sha256']
        frozen=json.loads(previous_plan.read_text())['frozen'];assert all(sha(ROOT/file)==digest for file,digest in frozen.items())
        paths += [previous_path,previous_plan]
        frozen.update({str(p.relative_to(ROOT)):sha(p) for p in paths})
        work=ROOT/'.work'/args.run_id;work.mkdir(exist_ok=False)
        write(work/'plan.json',dict(owner=str(ROOT),frozen=frozen,guest_commands=0,performance_measurement=False))
        modes=['cfg_without_callee_effects','cfg_with_callee_effects'];cases=[]
        for index,label in enumerate(['block','exhaustive']):
            require_space(ROOT,8)
            profile=json.loads((ROOT/'.work/guarded-local-facts-profile-01'/f'{index}-profile.json').read_text())
            calls=call_index(json.loads((ROOT/'.work/native-continuation-census-01'/f'{label}.json').read_text()),profile)
            folder=ROOT/'.work'/f'adopted-runtime-sample-{label}-01'/'0'
            mapping=json.loads((folder/'jit-code/operations.json').read_text())
            fine=json.loads((ROOT/'.work/native-protocol-census-01'/f'{label}.json').read_text())
            samples=[f for root in parse_tree((folder/'sample.txt').read_text()) for f in self_samples(root)]
            sampled,returns,parts,generated=attribute({k:dict(callee=k) for k in calls},mapping,fine,samples)
            assert len(profile['functions'])==len(functions)
            assert [f['function'] for f in functions]==list(range(len(functions)))
            assert all((pf['name'],pf['frame_size'])==(f['name'],f['frame_size']) for pf,f in zip(profile['functions'],functions))
            typed_calls={(f['function'],c['pc']):c for f in functions for c in f['calls']}
            histograms={mode:{'calls':Counter(),'clear_samples':Counter(),'sites':Counter()} for mode in modes}
            sites=[]
            for key,call in calls.items():
                c=typed_calls[key];assert c['callee']==call['callee']
                hits=call['hits'];callee=functions[c['callee']];clear=sampled[key]['call_frame_clear']
                verdicts={}
                for mode in modes:
                    proof=callee[mode]
                    reason='eligible' if c['caller_local_arguments'] and proof['eligible'] else (
                        'unproved_caller_arguments' if not c['caller_local_arguments'] else proof['decline']['reason'])
                    for field,value in [('calls',hits),('clear_samples',clear),('sites',1)]:histograms[mode][field][reason]+=value
                    verdicts[mode]=reason
                sites.append(dict(function=key[0],pc=key[1],callee=c['callee'],native_calls=hits,clear_samples=clear,
                    frame_bytes=callee['frame_size'],verdicts=verdicts))
            old=previous['cases'][index];assert old['case']==label and generated==old['generated_samples']
            assert sum(c['hits'] for c in calls.values())==old['native_calls']
            total_clear=parts['Call/call_frame_clear'];assert sum(s['clear_samples'] for s in sites)==total_clear
            for mode in modes:
                assert sum(histograms[mode]['calls'].values())==old['native_calls']
                assert sum(histograms[mode]['clear_samples'].values())==total_clear
            report=work/(label+'.json');write(report,dict(status='passed',case=label,sites=sites,histograms=histograms))
            cases.append(dict(case=label,native_calls=old['native_calls'],generated_samples=generated,clear_samples=total_clear,
                histograms=histograms,report_sha256=sha(report)))
            print(label,'clearing samples',total_clear,'eligible',histograms[modes[1]]['clear_samples']['eligible'],flush=True)
        assert all(sha(ROOT/file)==digest for file,digest in frozen.items())
        revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        for file,digest in frozen.items():
            if file.startswith(('crates/','benchmarks/','scripts/','results/')):
                spec=revision+':'+file;assert hashlib.sha256(subprocess.check_output(['git','show',spec],cwd=ROOT)).hexdigest()==digest
                history.append(dict(path=file,sha256=digest,git_source=spec))
        result=ROOT/'results'/args.run_id;result.mkdir(exist_ok=False)
        write(result/'source-bindings.json',dict(source_revision=revision,files=history))
        write(result/'summary.json',dict(status='passed',cases=cases,raw=str(work.relative_to(ROOT)),
            plan_sha256=sha(work/'plan.json'),unique_frozen_inputs=len(frozen),all_frozen_inputs_verified=True,
            historical_build_failures=1,git_bindings=len(history),source_bindings_sha256=sha(result/'source-bindings.json'),
            guest_commands=0,runtime_changes=0,performance_measurement=False,
            limitation='Coverage is an upper bound on clearing samples. Alignment padding remains cleared and future address guards have a cost.'))


if __name__=='__main__':main()
