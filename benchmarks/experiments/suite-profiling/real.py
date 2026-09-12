#!/usr/bin/env python3
"""Compare fresh catalog entries with exact profiled execution on real programs."""
from collections import Counter
import json
import os
import re
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from interpreter import installed_tools
from profile_vm_transitions import counts as checked_counts
from suite_reports import read_report,validate_report,validate_runtime_limits
from workflow_io import capture,require_space,write_json as write

CASES=[('token','filtered-workflow-token-02',[
    'token_phrase::tests::block_boundaries_preserve_maximal_runs_literal_gating_and_restart',
    'token_phrase::tests::exhaustive_small_byte_semantics_match_pinned_regex']),
    ('folded','filtered-workflow-folded-01',[
    'folded_literal_trie::tests::common_offset_prefilter_matches_scalar_reference_on_all_short_byte_strings_and_windows']),
    ('pgrust','filtered-workflow-pgrust-01',None)]


def distribution(profile,statistics):
    checked=checked_counts(profile,statistics)
    kinds=Counter();blocks=Counter();hot=[];region_entries=region_ops=0
    for fid,f in enumerate(profile['functions']):
        n=len(f['operations']);delta=[0]*(n+1)
        for pc,hits in enumerate(f['jit_blocks']):
            if not hits:continue
            end=f['jit_block_ends'][pc];length=end-pc
            delta[pc]+=hits;delta[end]-=hits
            label=next(label for upper,label in [(1,'1'),(4,'2..4'),(8,'5..8'),(16,'9..16'),(32,'17..32'),(64,'33..64'),(1024,'65..1024')] if length<=upper)
            blocks[label]+=hits
            variant=f['operations'][pc].split(' ',1)[0]
            if length!=1 or variant not in ['Call','Return']:
                region_entries+=hits;region_ops+=hits*length
        active=logical=0
        for pc,op in enumerate(f['operations']):
            active+=delta[pc];kinds[op.split(' ',1)[0]]+=active;logical+=active
        assert active+delta[n]==0
        if logical:
            hot.append(dict(function=fid,name_prefix=f['name'][:240],name_truncated=len(f['name'])>240,
                native_operations=logical,interpreted_operations=sum(f['interpreted']),
                native_block_entries=sum(f['jit_blocks']),frame_size=f['frame_size'],registers=f['registers']))
    assert sum(kinds.values())==statistics['jit_instructions']
    return dict(native_operations=checked['native_instructions'],interpreted_operations=checked['interpreted_instructions'],
        native_operations_by_variant=dict(kinds.most_common()),native_block_entries_by_length=dict(blocks),
        native_region_entries_excluding_single_call_return=region_entries,
        mean_native_region_operations=region_ops/region_entries if region_entries else None,
        top_native_functions=sorted(hot,key=lambda f:-f['native_operations'])[:12],
        limitation='Instrumented logical bytecode counters; block lengths do not predict machine cost. Operation labels group counts only; no operands or CFG edges inferred from Debug strings.')


def main():
    run='suite-profiling-real-01'
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,8)
        control_path=ROOT/'results/jit-register-width-build-02/summary.json'
        build_path=ROOT/'results/suite-profiling-build-02/summary.json'
        control=json.loads(control_path.read_text());build=json.loads(build_path.read_text())
        assert control['status']==build['status']=='passed'
        assert build['tests']['test-debug']==build['tests']['test-release']==dict(passed=340,ignored=1)
        tools={mode:installed_tools(s['tool_key'])[0] for mode,s in [('baseline',control),('profile',build)]}
        qualification=ROOT/'results/fixed-frame-clear-entropy-check-01/summary.json'
        q=json.loads(qualification.read_text());assert q['status']=='passed' and q['commands']==17 and q['expected_rejections']==10
        library=(ROOT/q['library']).resolve(strict=True);assert sha(library)==q['library_sha256']
        frozen_paths=[Path(__file__),Path(__file__).with_name('PLAN.md'),control_path,build_path,qualification,library]
        frozen_paths += [ROOT/'scripts'/n for n in ['profile_vm_transitions.py','suite_reports.py','workflow_io.py']]
        frozen_paths += [tool/'rust-interp-vm' for tool in tools.values()]
        inputs=[]
        for case,reference,names in CASES:
            summary_path=ROOT/'results'/reference/'summary.json';summary=json.loads(summary_path.read_text());assert summary['status']=='passed'
            records_path=ROOT/summary['raw']/'records.json';assert sha(records_path)==summary['records_sha256']
            row=next(r for r in json.loads(records_path.read_text()) if r['state']==6 and r['mode']=='automatic')
            artifact=ROOT/row['artifact_path'];catalog=Path(str(artifact)+'.entries.json')
            assert sha(artifact)==row['artifact_sha256'] and sha(catalog)==row['launch']['entry_catalog_sha256']
            suite_path=ROOT/summary['raw']/'6-automatic-suite.json';suite,_=read_report(suite_path,row['suite_sha256'])
            all_names=[t['name'] for t in suite['tests']];validate_report(suite,all_names,'prepared',True)
            frozen_paths += [summary_path,records_path,artifact,catalog,suite_path]
            for name in (names if names is not None else all_names):
                entry=next(e for e in json.loads(catalog.read_text())['entries'] if e['name']==name)
                inputs.append(dict(case=case,name=name,function=entry['function'],artifact=str(artifact.relative_to(ROOT)),
                    artifact_sha256=sha(artifact),catalog=str(catalog.relative_to(ROOT)),catalog_sha256=sha(catalog),limits=suite['runtime_limits']))
        frozen={str(p.relative_to(ROOT)):sha(p) for p in frozen_paths}
        work=ROOT/'.work'/run;work.mkdir(exist_ok=False)
        write(work/'plan.json',dict(owner=str(ROOT),baseline_key=control['tool_key'],profile_key=build['tool_key'],
            frozen=frozen,inputs=inputs,performance_measurement=False,
            scope='fresh single-entry control records entropy, catalog-selected profile replays it; no edited compilation or prepared-suite timing'))
        env={k:v for k,v in os.environ.items() if not k.startswith(('RUST_INTERP_','RUSTDEV_'))}
        assert not any(k.startswith('DYLD_') for k in env)
        env.update(DYLD_INSERT_LIBRARIES=str(library),RUST_INTERP_VM_STATS='1')
        records=[];summaries=[]
        for index,item in enumerate(inputs):
            tape=work/f'{index}.tape';profile_path=work/f'{index}-profile.json';suite_path=work/f'{index}-control.json'
            subset=json.loads((ROOT/item['catalog']).read_text());subset['entries']=[e for e in subset['entries'] if e['name']==item['name']]
            assert len(subset['entries'])==1;subset_path=work/f'{index}-catalog.json';write(subset_path,subset)
            pair={}
            for mode in ['baseline','profile']:
                require_space(ROOT,8)
                command=[str(tools[mode]/'rust-interp-vm'),'--engine','jit','--jit-resumable-calls','--jit-persistent-registers',
                    '--instruction-limit',str(item['limits']['instructions']),'--allocation-limit',str(item['limits']['allocations'])]
                if mode=='baseline':command+=['--isolated-batch','fresh','--suite-report',str(suite_path),'--suite-catalog',str(subset_path)]
                else:command+=['--profile',str(profile_path),'--profile-test',item['name'],'--suite-catalog',str(ROOT/item['catalog'])]
                command.append(str(ROOT/item['artifact']))
                child_env=dict(env,RUST_INTERP_ENTROPY_MODE='record' if mode=='baseline' else 'replay',RUST_INTERP_ENTROPY_TAPE=str(tape))
                child,stdout,stderr=capture(command,cwd=ROOT,env=child_env,receipt_path=work/'active.json',receipt=dict(index=index,case=item['case'],mode=mode))
                record=dict(index=index,mode=mode,command=command,pid=child.pid,returncode=child.returncode,stdout=stdout,stderr=stderr)
                records.append(record);write(work/'records.json',records)
                assert child.returncode==0 and stdout=='0\n',stderr
                stats={k:int(v) for k,v in re.findall(r'\b([a-z_]+)=(\d+)\b',stderr)}
                assert all(k in stats for k in ['entropy_calls','entropy_bytes'])
                if mode=='baseline':
                    suite,digest=read_report(suite_path);validate_report(suite,[item['name']],'fresh',True)
                    validate_runtime_limits(suite,item['limits']['instructions'],item['limits']['allocations'],required=True)
                    stats.update({k:suite['tests'][0][k] for k in ['instructions','peak_guest_memory','jit_declined_functions']})
                    record.update(suite_sha256=digest,subset_catalog_sha256=sha(subset_path))
                else:
                    selected=[json.loads(line.removeprefix('rust-interp-profile-selection: ')) for line in stderr.splitlines() if line.startswith('rust-interp-profile-selection: ')]
                    assert len(selected)==1
                    assert all(selected[0][k]==item[k] for k in ['name','function','artifact_sha256','catalog_sha256'])
                    assert profile_path.stat().st_size<=256*1024**2
                    diagnostic=distribution(json.loads(profile_path.read_text()),stats)
                    summaries.append(dict(index=index,**item,profile_sha256=sha(profile_path),selection=selected[0],
                        statistics=stats,distribution=diagnostic))
                    record.update(profile_sha256=sha(profile_path),selection=selected[0])
                assert stats['jit_declined_functions']==0
                pair[mode]={k:stats[k] for k in ['instructions','peak_guest_memory','entropy_calls','entropy_bytes']}
                record.update(statistics=stats,tape_sha256=sha(tape));write(work/'records.json',records)
            assert pair['baseline']==pair['profile'],item['name']+' changed exact execution'
            write(work/'profiles.json',summaries)
            print(index,item['name'],'PASS',pair['profile']['instructions'],'logical instructions',flush=True)
        assert all(sha(ROOT/p)==h for p,h in frozen.items())
        result=ROOT/'results'/run;result.mkdir(exist_ok=False)
        write(result/'summary.json',dict(status='passed',commands=len(records),profiled_tests=len(summaries),
            baseline_key=control['tool_key'],profile_key=build['tool_key'],exact_logical_counts_and_entropy=True,
            saved_artifacts_unchanged=True,jit_declines=0,performance_measurement=False,profiles=summaries,
            raw=str(work.relative_to(ROOT)),plan_sha256=sha(work/'plan.json'),records_sha256=sha(work/'records.json')))


if __name__=='__main__':main()
