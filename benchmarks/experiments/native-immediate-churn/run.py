"""Explain exact field churn in closed artifact pairs, without executing guests."""
import json,os,shutil,statistics,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write
NAME='native-immediate-churn-01'
def read(p):return json.loads(p.read_text())


def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45)
        target=ROOT/'.work/fixed-frame-clear-combined-build-01/target'
        allocated=int(subprocess.check_output(['du','-sk',str(target)],text=True).split()[0])*1024
        needed=max(14*1024**3,8*1024**3+2*allocated)
        assert shutil.disk_usage(ROOT).free>=needed,'insufficient conservative build admission'
        frozen={}
        def bind(p,h=None):
            p=Path(p);actual=sha(p)
            if h is not None:assert actual==h,p
            frozen[str(p.relative_to(ROOT))]=actual
            return read(p) if p.suffix=='.json' else actual
        folder=ROOT/'results/native-reuse-identity-census-01';closed=bind(folder/'closure.json')
        assert closed['status']=='closed' and closed['all_hashes_verified']
        saved=bind(folder/'summary.json',closed['summary_sha256']);bind(folder/'terminal.json',closed['terminal_sha256'])
        assert saved['status']=='passed' and saved['artifacts']==17 and saved['new_guest_commands']==0
        raw=ROOT/saved['raw'];old_plan=bind(raw/'plan.json',saved['plan_sha256'])
        for path,digest in saved['artifacts_sha256'].items():bind(ROOT/path,digest)
        artifacts={item['sha256']:dict(artifact=item['artifact'],sha256=item['sha256']) for item in read(raw/'inputs.json')}
        for item in artifacts.values():bind(Path(item['artifact']),item['sha256'])
        comparisons=read(raw/'comparisons.json');assert len(comparisons)==14
        work=ROOT/'.work'/NAME
        pairs=[dict(case=row['case'],cycle=row['cycle'],state=row['state'],before=artifacts[row['previous_artifact_sha256']],
            after=artifacts[row['artifact_sha256']],output=str(work/f'{i}.json'),
            expected_changed_ids=sorted(set(range(row['metrics']['functions']))-set(row['identities']['self_equal'])))
            for i,row in enumerate(comparisons)]
        paths=subprocess.check_output(['git','ls-files','crates','Cargo.toml','Cargo.lock','rust-toolchain.toml'],text=True).splitlines()
        paths += [str(p.relative_to(ROOT)) for p in Path(__file__).parent.iterdir() if p.suffix in ['.py','.md']]
        paths += ['scripts/compare_saved_runtime.py','scripts/workflow_io.py']
        for p in paths:bind(ROOT/p)
        revision=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
        assert not subprocess.check_output(['git','diff','--name-only','HEAD']).strip()
        work.mkdir(exist_ok=False);write(work/'inputs.json',pairs)
        write(work/'plan.json',dict(owner=str(ROOT),source_revision=revision,frozen=frozen,pairs=len(pairs),
            inputs_sha256=sha(work/'inputs.json'),artifacts=len(artifacts),target=str(target.relative_to(ROOT)),
            required_free_bytes=needed,allocated_target_bytes=allocated,expected_commands=1,rust_controls=2,
            guest_commands=0,code_publications=0,production_changes=0,minimum_child_gib=8,performance_measurement=False))
        records=[];write(work/'records.json',records)
        env={k:v for k,v in os.environ.items() if not k.startswith(('RUST_INTERP_','RUSTDEV_','CARGO_','NATIVE_IDENTITY_','NATIVE_CHURN_'))
            and k not in ['RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','RUSTC','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER','RUST_TEST_THREADS']}
        assert not any(k.startswith('DYLD_') for k in env)
        env.update(CARGO_INCREMENTAL='0',CARGO_PROFILE_RELEASE_DEBUG='1',CARGO_PROFILE_DEV_DEBUG='0',CARGO_PROFILE_TEST_DEBUG='0',
            CARGO_TERM_COLOR='never',PYTHONDONTWRITEBYTECODE='1',RUST_TEST_THREADS='2',NATIVE_CHURN_INPUT=str(work/'inputs.json'))
        command=['cargo','+nightly-2026-09-08','test','--release','--lib','-p','rust-interp-bytecode','--locked','--offline','--jobs','2',
            '--manifest-path',str(ROOT/'Cargo.toml'),'--target-dir',str(target),'native_identity_census::churn::','--','--include-ignored']
        require_space(ROOT,8);assert shutil.disk_usage(ROOT).free>=needed,'build admission no longer holds'
        started=time.time();child,out,err=capture(command,cwd=ROOT,env=env,receipt_path=work/'active.json',receipt=dict(label='0'))
        for stream,data in [('stdout',out),('stderr',err)]:(work/f'0.{stream}').write_text(data)
        records.append(dict(label='0',command=command,cwd=str(ROOT),pid=child.pid,returncode=child.returncode,seconds=time.time()-started,
            stdout_sha256=sha(work/'0.stdout'),stderr_sha256=sha(work/'0.stderr')))
        write(work/'records.json',records);assert child.returncode==0,(out+err)[-4500:]
        assert 'test result: ok. 3 passed; 0 failed; 0 ignored;' in out
        observations=[]
        for i,pair in enumerate(pairs):
            detail=read(work/f'{i}.json');assert detail['status']=='passed'
            assert detail['before_sha256']==pair['before']['sha256'] and detail['after_sha256']==pair['after']['sha256']
            assert [r['function'] for r in detail['rows']]==pair['expected_changed_ids']
            assert detail['guest_commands']==detail['code_publications']==0 and not detail['address_relocation_proven']
            observations.append(dict(case=pair['case'],cycle=pair['cycle'],state=pair['state'],**detail['summary'],
                top_deltas=sorted(detail['deltas'].items(),key=lambda item:(-item[1],item[0]))[:12],detail_sha256=sha(work/f'{i}.json')))
        groups=[]
        for case in ['token','parser']:
            selected=[r for r in observations if r['case']==case and r['state']>0];assert len(selected)==5
            fields=['functions','changed_functions','immediate_only_functions','name_changes','layout_changes',
                'code_length_changes','changed_immediates','both_numbers_fit_data','equal_16_byte_data_windows']
            groups.append(dict(case=case,edited_states=5,medians={k:statistics.median(r[k] for r in selected) for k in fields},states=selected))
        assert all(sha(ROOT/p)==h for p,h in frozen.items())
        out=ROOT/'results'/NAME;out.mkdir(exist_ok=False);write(out/'observations.json',observations)
        write(out/'summary.json',dict(status='passed',source_revision=revision,commands=1,controls=2,pairs=14,artifacts=17,
            new_guest_commands=0,production_changes=0,code_publications=0,address_relocation_proven=False,
            cases=groups,setup_seconds=records[0]['seconds'],raw=str(work.relative_to(ROOT)),
            plan_sha256=sha(work/'plan.json'),records_sha256=sha(work/'records.json'),
            artifacts_sha256={str(p.relative_to(ROOT)):sha(p) for p in [work/'inputs.json',out/'observations.json',*[work/f'{i}.json' for i in range(len(pairs))]]},
            performance_measurement=False,scope='Exact field differences with complete typed validation and independently reconciled changed function IDs. Numeric data-range/window matches are ambiguous, never address provenance or cache-key permission.'))
        print(json.dumps(dict(cases=[dict(case=c['case'],medians=c['medians']) for c in groups],pairs=14)),flush=True)


if __name__=='__main__':main()
