#!/usr/bin/env python3
"""Compare native, explicit and automatic suites across pinned production edits."""
import argparse,hashlib,json,os,statistics,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from interpreter import installed_tools,require_export_option
from workflow_cases import WORKFLOWS,WORKFLOW_VARIANTS
from workflow_measurements import source_states,child_usage,child_cpu_since
from workflow_io import capture,require_space,write_json as write,SourceEdit
from test_discovery import read_selection,read_listing
from suite_reports import read_report,validate_report,validate_runtime_limits

CASES={'pgrust':('pgrust',None,'','prepared-catalog-pgrust-03'),
       'folded':('fre','folded-literal-trie','folded_literal_trie::tests::','prepared-suite-folded-01'),
       'token':('fre','token-phrase-allocation','token_phrase::tests::','prepared-suite-token-01')}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--case',choices=CASES,required=True);parser.add_argument('--run-id',required=True);args=parser.parse_args()
    assert args.run_id.startswith('filtered-workflow-'+args.case+'-') and Path(args.run_id).name==args.run_id
    project,variant,pattern,reference=CASES[args.case];case=WORKFLOWS[project] if variant is None else WORKFLOW_VARIANTS[project,variant]
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,8 if project=='pgrust' else 9)
        build_path=ROOT/'results/filtered-suites-build-02/summary.json';build=json.loads(build_path.read_text());assert build['status']=='passed'
        qualification=ROOT/'results/filtered-suites-fixture-02/summary.json';assert json.loads(qualification.read_text())['status']=='passed'
        tool,key=installed_tools(build['tool_key']);require_export_option(tool,key,'filtered-tests')
        ref_path=ROOT/'results'/reference/'summary.json';ref=json.loads(ref_path.read_text())
        listing_path=ROOT/'.work/test-discovery-real-01'/(project+'-tests.json');listing,_=read_listing(listing_path)
        names=[t['name'] for t in listing['tests'] if pattern in t['name'] and not t['ignored']]
        assert names and all(t['ordinary_test'] for t in listing['tests'] if t['name'] in names) and set(case['tests'])<=set(names)
        source=ROOT/'.work/sources'/project;marker=source/'.rust-interp-owned.json';owned=json.loads(marker.read_text())
        assert owned['owner']==str(ROOT) and owned['revision']==ref['revision']
        assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip()==ref['revision']
        assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=source,text=True).strip()
        path=source/case['file'];original=path.read_bytes();states=list(source_states(original.decode(),case,1,['native','explicit','automatic'],True))
        work=ROOT/'.work'/args.run_id;work.mkdir(exist_ok=False)
        env={k:v for k,v in os.environ.items() if not k.startswith(('RUST_INTERP_','RUSTDEV_','CARGO_PROFILE_')) and k not in ['RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','RUSTC','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER','CARGO_INCREMENTAL','CARGO_TARGET_DIR','CARGO_BUILD_TARGET']}
        assert not any(k.startswith('DYLD_') for k in env)
        env.update(CARGO_TERM_COLOR='never',RUST_INTERP_LAUNCH_STATS='1')
        if ref.get('build_tool_opt_level') is not None:
            for profile in ['DEV','TEST']:env['CARGO_PROFILE_'+profile+'_BUILD_OVERRIDE_OPT_LEVEL']=str(ref['build_tool_opt_level'])
        guest_env=env.copy()
        if ref['guest_rustflags']:guest_env['RUSTFLAGS']=' '.join(ref['guest_rustflags'])
        frozen_paths=[Path(__file__),Path(__file__).with_name('FILTERED.md'),build_path,qualification,ref_path,listing_path,marker]
        frozen_paths += [ROOT/'scripts'/n for n in ['interpreter.py','test_discovery.py','workflow_cases.py','workflow_io.py','workflow_measurements.py','suite_reports.py','native_suite.py','std_mir.py']]
        frozen_paths += [tool/n for n in ['rust-interp-vm','rust-interp-mir-export','rust-interp-rustc-wrapper']]
        for rel in subprocess.check_output(['git','ls-files','-z'],cwd=source).decode().split('\0'):
            if rel and source/rel!=path:frozen_paths.append(source/rel)
        frozen={str(p.relative_to(ROOT)):sha(p) for p in frozen_paths}
        plan=dict(owner=str(ROOT),case=case,filter=pattern,names=names,tool_key=key,revision=ref['revision'],frozen=frozen,
            original_source_sha256=sha(path),minimum_child_gib=8,profiles='repository for native and both custom modes; two Cargo workers',
            runtime_limits=dict(instructions=ref['instruction_limit'],allocations=ref['allocation_limit']),guest_rustflags=ref['guest_rustflags'],
            comparison='one descriptive cycle; separate incremental Cargo caches; prepared isolated JIT in both custom modes; one native process per selected test; token expands the old three-test subset to the full twelve-test module')
        write(work/'plan.json',plan);rows=[];transitions=[];previous={mode:None for mode in ['native','explicit','automatic','check']}
        def execute(mode,state,label,success):
            suite_path=work/(f'{state}-{mode}-suite.json');digest=sha(path)
            assert previous[mode]!=digest,'unchanged source entered edited command'
            if mode in ['native','check']:
                command=([sys.executable,str(ROOT/'scripts/native_suite.py')] if mode=='native' else ['cargo','+nightly-2026-09-08','check'])+['--manifest-path',str(source/'Cargo.toml'),'--package',case['package'],'--target-dir',str(work/mode),'--jobs','2']
                if mode=='check':command+=['--lib','--profile','test','--locked','--offline']
                else:
                    command+=['--test-threads=1','--suite-report',str(suite_path)]
                    for name in names:command+=['--entry',name]
                child_env=env
            else:
                command=[sys.executable,str(ROOT/'scripts/interpreter.py'),'--manifest-path',str(source/'Cargo.toml'),'--package',case['package'],'--jobs','2','--tool-key',key,'--cache-namespace',args.run_id+':'+mode,'--test-body','--std-mir','--engine','jit','--jit-resumable-calls','--jit-persistent-registers','--isolated-batch','prepared','--suite-report',str(suite_path),'--instruction-limit',str(ref['instruction_limit'])]
                if ref.get('allocation_limit') is not None:command+=['--allocation-limit',str(ref['allocation_limit'])]
                for field in ['inline_leaves','trap_unsupported_calls','run_try_callbacks']:
                    if ref.get(field):command+=['--'+field.replace('_','-')]
                if mode=='automatic':command+=['--test-filter',pattern]
                else:
                    for name in names:command+=['--entry',name]
                child_env=guest_env
            require_space(ROOT,8);before=child_usage();started=time.perf_counter()
            child,stdout,stderr=capture(command,cwd=source,env=child_env,receipt_path=work/'active.json',receipt=dict(state=state,mode=mode,label=label))
            row=dict(mode=mode,state=state,label=label,command=command,seconds=time.perf_counter()-started,cpu=child_cpu_since(before),returncode=child.returncode,stdout=stdout,stderr=stderr,source_sha256=digest,previous_source_sha256=previous[mode]);rows.append(row);write(work/'records.json',rows)
            assert sha(path)==digest and (child.returncode==0)==(success or mode=='check'),stderr
            assert ('Compiling ' if mode=='native' else 'Checking ')+case['package'] in stderr
            if mode!='check':
                suite,suite_digest=read_report(suite_path);row['outcomes']=validate_report(suite,names,'native' if mode=='native' else 'prepared',success);row['suite_sha256']=suite_digest
            if mode in ['explicit','automatic']:
                validate_runtime_limits(suite,ref['instruction_limit'],ref['allocation_limit'],required=True)
                launch=[json.loads(line.removeprefix('rust-interp-launch: ')) for line in stderr.splitlines() if line.startswith('rust-interp-launch: ')]
                assert len(launch)==1;launch=launch[0];row['launch']=launch;artifact=Path(launch['artifact_path']);assert sha(artifact)==launch['artifact_sha256']
                assert sum(line.startswith('rust-interp-export: ') for line in stderr.splitlines())==1
                snapshot=work/f'{state}-{mode}.rbc';snapshot.write_bytes(artifact.read_bytes());row['artifact_path']=str(snapshot.relative_to(ROOT));row['artifact_sha256']=sha(snapshot)
                catalog=Path(launch['entry_catalog_path']);assert sha(catalog)==launch['entry_catalog_sha256'];entries=json.loads(catalog.read_text())['entries']
                assert [e['name'] for e in entries]==names and [e['function'] for e in entries]==[t['function'] for t in suite['tests']]
                Path(str(snapshot)+'.entries.json').write_bytes(catalog.read_bytes())
                if mode=='automatic':
                    selection,d=read_selection(Path(launch['test_selection_path']),artifact,pattern,False);assert selection['selected']==names and d==launch['test_selection_sha256']
                    Path(str(snapshot)+'.selection.json').write_bytes(Path(launch['test_selection_path']).read_bytes())
            previous[mode]=digest;write(work/'records.json',rows);print(state,mode,round(row['seconds'],3),flush=True)
            return row
        with SourceEdit(path,original) as edit:
            for state in states+[dict(state=6,label='restored-original',source=original,modes=['native','explicit','automatic'])]:
                before=sha(path);edit.replace(state['source']);transitions.append(dict(state=state['state'],before=before,after=sha(path)));write(work/'transitions.json',transitions)
                selected=[execute(mode,state['state'],state['label'],state['state']!=-1) for mode in state['modes']]
                assert len({tuple(map(tuple,row['outcomes'])) for row in selected})==1
                assert len({row['artifact_sha256'] for row in selected if row['mode']!='native'})==1
                execute('check',state['state'],state['label'],True)
        assert path.read_bytes()==original and all(sha(ROOT/p)==h for p,h in frozen.items())
        pairs=[]
        for state in range(1,6):
            modes={r['mode']:r for r in rows if r['state']==state}
            pairs.append(dict(state=state,wall_ratio=modes['automatic']['seconds']/modes['explicit']['seconds'],cpu_ratio=modes['automatic']['cpu']['total_seconds']/modes['explicit']['cpu']['total_seconds']))
        out=ROOT/'results'/args.run_id;out.mkdir(exist_ok=False)
        write(out/'summary.json',dict(status='passed',project=project,case=args.case,test_count=len(names),tests=names,filter=pattern,
            tool_key=key,commands=len(rows),edited_pairs=5,source_restored=True,test_source_unchanged=True,automatic_explicit_bytecode_identical=True,
            all_native_assertion_outcomes_match=True,paired_wall_ratio=statistics.median(p['wall_ratio'] for p in pairs),paired_cpu_ratio=statistics.median(p['cpu_ratio'] for p in pairs),pairs=pairs,
            median_edited_seconds={m:statistics.median(r['seconds'] for r in rows if r['mode']==m and 1<=r['state']<=5) for m in ['native','explicit','automatic','check']},
            timing_scope=plan['comparison'],raw=str(work.relative_to(ROOT)),plan_sha256=sha(work/'plan.json'),records_sha256=sha(work/'records.json'),transitions_sha256=sha(work/'transitions.json')))
        print('PASS: native assertions and identical explicit/automatic bytecode across real edits',flush=True)


if __name__=='__main__':main()
