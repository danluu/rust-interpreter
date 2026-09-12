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
from workspace_cache import external_cache_root,cache_subdirectory

CASES={'pgrust':('pgrust',None,'','prepared-catalog-pgrust-03'),
       'folded':('fre','folded-literal-trie','folded_literal_trie::tests::','prepared-suite-folded-01'),
       'token':('fre','token-phrase-allocation','token_phrase::tests::','prepared-suite-token-01')}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--case',choices=CASES,required=True);parser.add_argument('--run-id',required=True)
    parser.add_argument('--workspace-cache-root',type=Path,help='existing parent for every mode\'s build caches; evidence stays in the repository')
    args=parser.parse_args()
    assert args.run_id.startswith('constant-fold-screen-'+args.case+'-') and Path(args.run_id).name==args.run_id
    project,variant,pattern,reference=CASES[args.case];case=WORKFLOWS[project] if variant is None else WORKFLOW_VARIANTS[project,variant]
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45)
        cache_root=ROOT if args.workspace_cache_root is None else external_cache_root(args.workspace_cache_root,ROOT)
        require_space(cache_root,8.3 if project=='pgrust' else 9.5)
        require_space(ROOT,8)
        build_paths={m:ROOT/'results'/r/'summary.json' for m,r in [('baseline','suite-profiling-build-02'),('candidate','constant-fold-compose-02')]}
        builds={m:json.loads(p.read_text()) for m,p in build_paths.items()};assert builds['baseline']['status']=='passed' and builds['candidate']['status']=='composed'
        qualification=ROOT/'results/constant-fold-saved-02/summary.json';assert json.loads(qualification.read_text())['status']=='passed'
        fixture=ROOT/'results/constant-fold-fixture-01/summary.json';proof=json.loads(fixture.read_text());assert proof['status']=='passed' and proof['original_tests']==9 and proof['exact_whole_artifact_constant_folding']
        assert proof['tools']=={mode:b['tool_key'] for mode,b in builds.items()}
        assert json.loads(qualification.read_text())['source_commit']==builds['candidate']['source_commit']
        assert builds['baseline']['binaries']['rust-interp-vm']==builds['candidate']['binaries']['rust-interp-vm']
        verifier=ROOT/builds['candidate']['verifier'];assert sha(verifier)==builds['candidate']['verifier_sha256']
        tools={m:installed_tools(b['tool_key'])[0] for m,b in builds.items()}
        for m,t in tools.items():require_export_option(t,builds[m]['tool_key'],'filtered-tests')
        if args.case!='token':
            primary=json.loads((ROOT/'results/constant-fold-screen-token-01/summary.json').read_text());assert primary['gate_passed']
        ref_path=ROOT/'results'/reference/'summary.json';ref=json.loads(ref_path.read_text())
        listing_path=ROOT/'.work/test-discovery-real-01'/(project+'-tests.json');listing,_=read_listing(listing_path)
        names=[t['name'] for t in listing['tests'] if pattern in t['name'] and not t['ignored']]
        assert names and all(t['ordinary_test'] for t in listing['tests'] if t['name'] in names) and set(case['tests'])<=set(names)
        source=ROOT/'.work/sources'/project;marker=source/'.rust-interp-owned.json';owned=json.loads(marker.read_text())
        assert owned['owner']==str(ROOT) and owned['revision']==ref['revision']
        assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip()==ref['revision']
        assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=source,text=True).strip()
        path=source/case['file'];original=path.read_bytes();states=list(source_states(original.decode(),case,1,['native','baseline','candidate'],True))
        work=ROOT/'.work'/args.run_id;work.mkdir(exist_ok=False)
        cache_work=work
        if args.workspace_cache_root is not None:
            cache_work=cache_subdirectory(cache_root,'benchmarks')/args.run_id
            cache_work.mkdir(exist_ok=False)
        env={k:v for k,v in os.environ.items() if not k.startswith(('RUST_INTERP_','RUSTDEV_','CARGO_PROFILE_')) and k not in ['RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','RUSTC','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER','CARGO_INCREMENTAL','CARGO_TARGET_DIR','CARGO_BUILD_TARGET']}
        assert not any(k.startswith('DYLD_') for k in env)
        env.update(CARGO_TERM_COLOR='never',RUST_INTERP_LAUNCH_STATS='1')
        if ref.get('build_tool_opt_level') is not None:
            for profile in ['DEV','TEST']:env['CARGO_PROFILE_'+profile+'_BUILD_OVERRIDE_OPT_LEVEL']=str(ref['build_tool_opt_level'])
        guest_env=env.copy()
        if ref['guest_rustflags']:guest_env['RUSTFLAGS']=' '.join(ref['guest_rustflags'])
        frozen_paths=[Path(__file__),Path(__file__).with_name('SCREEN.md'),*build_paths.values(),qualification,fixture,verifier,ref_path,listing_path,marker]
        frozen_paths += [ROOT/'scripts'/n for n in ['interpreter.py','workspace_cache.py','test_discovery.py','workflow_cases.py','workflow_io.py','workflow_measurements.py','suite_reports.py','native_suite.py','std_mir.py']]
        frozen_paths += [tool/n for tool in tools.values() for n in ['rust-interp-vm','rust-interp-mir-export','rust-interp-rustc-wrapper']]
        for rel in subprocess.check_output(['git','ls-files','-z'],cwd=source).decode().split('\0'):
            if rel and source/rel!=path:frozen_paths.append(source/rel)
        frozen={str(p.relative_to(ROOT)):sha(p) for p in frozen_paths}
        plan=dict(owner=str(ROOT),case=case,filter=pattern,names=names,tools={m:b['tool_key'] for m,b in builds.items()},revision=ref['revision'],frozen=frozen,
            original_source_sha256=sha(path),minimum_child_gib=8,profiles='repository for native and both custom modes; two Cargo workers',
            cache_parent=None if args.workspace_cache_root is None else str(args.workspace_cache_root.resolve()),cache_work=str(cache_work),evidence_root=str(work),
            runtime_limits=dict(instructions=ref['instruction_limit'],allocations=ref['allocation_limit']),guest_rustflags=ref['guest_rustflags'],
            comparison='Five paired cumulative production-body edits; complete commands include strict checking, export and all selected assertions. Independent fresh Cargo caches, identical VM/profiles/limits/workers, native/check controls. Original/wrong/restored states are outside timing medians.',minimum_token_wall_improvement=0.10,maximum_token_cpu_ratio=1.0,maximum_guard_wall_and_cpu_ratio=1.05)
        write(work/'plan.json',plan);rows=[];transitions=[];verifications=[];previous={mode:None for mode in ['native','baseline','candidate','check']}
        def execute(mode,state,label,success):
            suite_path=work/(f'{state}-{mode}-suite.json');digest=sha(path)
            assert previous[mode]!=digest,'unchanged source entered edited command'
            if mode in ['native','check']:
                command=([sys.executable,str(ROOT/'scripts/native_suite.py')] if mode=='native' else ['cargo','+nightly-2026-09-08','check'])+['--manifest-path',str(source/'Cargo.toml'),'--package',case['package'],'--target-dir',str(cache_work/mode),'--jobs','2']
                if mode=='check':command+=['--lib','--profile','test','--locked','--offline']
                else:
                    command+=['--test-threads=1','--suite-report',str(suite_path)]
                    for name in names:command+=['--entry',name]
                child_env=env
            else:
                command=[sys.executable,str(ROOT/'scripts/interpreter.py'),'--manifest-path',str(source/'Cargo.toml'),'--package',case['package'],'--jobs','2','--tool-key',builds[mode]['tool_key'],'--cache-namespace',args.run_id+':'+mode,'--test-body','--std-mir','--engine','jit','--jit-resumable-calls','--jit-persistent-registers','--isolated-batch','prepared','--suite-report',str(suite_path),'--instruction-limit',str(ref['instruction_limit'])]
                if ref.get('allocation_limit') is not None:command+=['--allocation-limit',str(ref['allocation_limit'])]
                if args.workspace_cache_root is not None:command+=['--workspace-cache-root',str(args.workspace_cache_root.resolve())]
                for field in ['inline_leaves','trap_unsupported_calls','run_try_callbacks']:
                    if ref.get(field):command+=['--'+field.replace('_','-')]
                command+=['--test-filter',pattern]
                child_env=guest_env
            require_space(ROOT,8);require_space(cache_root,8);before=child_usage();started=time.perf_counter()
            child,stdout,stderr=capture(command,cwd=source,env=child_env,receipt_path=work/'active.json',receipt=dict(state=state,mode=mode,label=label))
            row=dict(mode=mode,state=state,label=label,command=command,seconds=time.perf_counter()-started,cpu=child_cpu_since(before),returncode=child.returncode,stdout=stdout,stderr=stderr,source_sha256=digest,previous_source_sha256=previous[mode]);rows.append(row);write(work/'records.json',rows)
            assert sha(path)==digest and (child.returncode==0)==(success or mode=='check'),stderr
            assert ('Compiling ' if mode=='native' else 'Checking ')+case['package'] in stderr
            if mode!='check':
                suite,suite_digest=read_report(suite_path);row['outcomes']=validate_report(suite,names,'native' if mode=='native' else 'prepared',success);row['suite_sha256']=suite_digest
            if mode in ['baseline','candidate']:
                validate_runtime_limits(suite,ref['instruction_limit'],ref['allocation_limit'],required=True)
                launch=[json.loads(line.removeprefix('rust-interp-launch: ')) for line in stderr.splitlines() if line.startswith('rust-interp-launch: ')]
                assert len(launch)==1;launch=launch[0];row['launch']=launch;artifact=Path(launch['artifact_path']);assert sha(artifact)==launch['artifact_sha256']
                assert sum(line.startswith('rust-interp-export: ') for line in stderr.splitlines())==1
                snapshot=work/f'{state}-{mode}.rbc';snapshot.write_bytes(artifact.read_bytes());row['artifact_path']=str(snapshot.relative_to(ROOT));row['artifact_sha256']=sha(snapshot)
                catalog=Path(launch['entry_catalog_path']);assert sha(catalog)==launch['entry_catalog_sha256'];entries=json.loads(catalog.read_text())['entries']
                assert [e['name'] for e in entries]==names and [e['function'] for e in entries]==[t['function'] for t in suite['tests']]
                Path(str(snapshot)+'.entries.json').write_bytes(catalog.read_bytes())
                if mode in ['baseline','candidate']:
                    selection,d=read_selection(Path(launch['test_selection_path']),artifact,pattern,False);assert selection['selected']==names and d==launch['test_selection_sha256']
                    Path(str(snapshot)+'.selection.json').write_bytes(Path(launch['test_selection_path']).read_bytes())
            previous[mode]=digest;write(work/'records.json',rows);print(state,mode,round(row['seconds'],3),flush=True)
            return row
        with SourceEdit(path,original) as edit:
            for state in states+[dict(state=6,label='restored-original',source=original,modes=['native','baseline','candidate'])]:
                before=sha(path);edit.replace(state['source']);transitions.append(dict(state=state['state'],before=before,after=sha(path)));write(work/'transitions.json',transitions)
                selected=[execute(mode,state['state'],state['label'],state['state']!=-1) for mode in state['modes']]
                assert len({tuple(map(tuple,row['outcomes'])) for row in selected})==1
                execute('check',state['state'],state['label'],True)
                # Verification runs outside every measured child-tree interval.
                artifacts={r['mode']:ROOT/r['artifact_path'] for r in selected if r['mode']!='native'}
                verification=work/(str(state['state'])+'-folding.json')
                command=[str(verifier),'--verify-fold',str(artifacts['baseline']),str(artifacts['candidate']),str(verification)]
                require_space(ROOT,8)
                child,stdout,stderr=capture(command,cwd=ROOT,env=env,receipt_path=work/'verification-active.json',receipt=dict(state=state['state']))
                part=dict(state=state['state'],command=command,pid=child.pid,returncode=child.returncode,stdout=stdout,stderr=stderr)
                verifications.append(part);write(work/'verifications.json',verifications)
                assert child.returncode==0,stderr
                assert json.loads(verification.read_text())['exact_constant_fold']
                part['report_sha256']=sha(verification);write(work/'verifications.json',verifications)
        assert path.read_bytes()==original and all(sha(ROOT/p)==h for p,h in frozen.items())
        pairs=[]
        for state in range(1,6):
            modes={r['mode']:r for r in rows if r['state']==state}
            pairs.append(dict(state=state,wall_ratio=modes['candidate']['seconds']/modes['baseline']['seconds'],cpu_ratio=modes['candidate']['cpu']['total_seconds']/modes['baseline']['cpu']['total_seconds']))
        wall_ratio=statistics.median(p['wall_ratio'] for p in pairs);cpu_ratio=statistics.median(p['cpu_ratio'] for p in pairs)
        gate_passed=(wall_ratio<=0.90 and cpu_ratio<=1.0) if args.case=='token' else (wall_ratio<=1.05 and cpu_ratio<=1.05)
        out=ROOT/'results'/args.run_id;out.mkdir(exist_ok=False)
        write(out/'summary.json',dict(status='passed',gate_passed=gate_passed,performance_screen_only=True,project=project,case=args.case,test_count=len(names),tests=names,filter=pattern,
            tools={m:b['tool_key'] for m,b in builds.items()},commands=len(rows),edited_pairs=5,source_restored=True,test_source_unchanged=True,vm_bytes_identical=True,bytecode_changes_expected=True,exact_constant_fold_pairs=len(verifications),verification_commands=len(verifications),verifications_sha256=sha(work/'verifications.json'),
            all_native_assertion_outcomes_match=True,paired_wall_ratio=wall_ratio,paired_cpu_ratio=cpu_ratio,pairs=pairs,
            median_edited_seconds={m:statistics.median(r['seconds'] for r in rows if r['mode']==m and 1<=r['state']<=5) for m in ['native','baseline','candidate','check']},
            timing_scope=plan['comparison'],raw=str(work.relative_to(ROOT)),plan_sha256=sha(work/'plan.json'),records_sha256=sha(work/'records.json'),transitions_sha256=sha(work/'transitions.json')))
        print('PASS: source transitions and native assertions; performance gate',gate_passed,'wall',wall_ratio,'CPU',cpu_ratio,flush=True)


if __name__=='__main__':main()
