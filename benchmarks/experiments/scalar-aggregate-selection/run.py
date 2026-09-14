"""Check isolated exhaustive selection against two closed native source versions."""
import hashlib,json,os,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_saved_runtime import acquire_lock,sha
from workflow_io import capture,require_space,write_json as write
from workflow_cases import WORKFLOW_VARIANTS
NAME='scalar-aggregate-selection-01'
TEST='token_phrase::tests::exhaustive_small_byte_semantics_match_pinned_regex'
def read(p):return json.loads(p.read_text())
def main():
    with (ROOT/'.work/benchmark.lock').open('a') as lock:
        acquire_lock(lock,45);require_space(ROOT,12)
        frozen={}
        def bind(p,h=None):
            digest=sha(p)
            if h is not None:assert digest==h,p
            frozen[str(p.relative_to(ROOT))]=digest
            return read(p) if p.suffix=='.json' else None
        old=ROOT/'.work/scalar-path-screen-token-01'
        closed=bind(ROOT/'results/scalar-path-screen-token-01/closure.json');assert closed['status']=='passed'
        evidence=bind(ROOT/closed['evidence_path'],closed['evidence_sha256'])
        prior=bind(old/'plan.json',evidence[str((old/'plan.json').relative_to(ROOT))])
        records=bind(old/'records.json',evidence[str((old/'records.json').relative_to(ROOT))])
        source=ROOT/'.work/sources/fre';marker=source/'.rust-interp-owned.json'
        owner=bind(marker,evidence[str(marker.relative_to(ROOT))]);assert owner['owner']==str(ROOT) and owner['revision']==prior['revision']
        assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip()==prior['revision']
        assert not subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=source).strip()
        case=WORKFLOW_VARIANTS['fre','token-phrase-allocation'];assert case['negative']==prior['case']['negative']
        path=source/case['file'];bind(path,prior['original_source_sha256']);original=path.read_text()
        _,before,after=case['negative'];assert original.count(before)==1
        wrong=hashlib.sha256(original.replace(before,after,1).encode()).hexdigest()
        cases=[]
        for label,phase,digest,code,outcome in [('original','cold',sha(path),0,'passed'),('wrong','wrong-edit',wrong,101,'failed')]:
            row,=[r for r in records if r['mode']=='native' and r['phase']==phase]
            assert row['source_sha256']==digest and row['returncode']==code and [TEST,outcome] in row['outcomes']
            exe=ROOT/row['native_executable']['path'];bind(exe,row['native_executable']['sha256']);assert sha(exe)==evidence[str(exe.relative_to(ROOT))]
            cases.append(dict(label=label,executable=str(exe),source_sha256=digest,expected_returncode=code,expected_outcome=outcome))
        for p in [*Path(__file__).parent.iterdir(),*(ROOT/'scripts'/n for n in ['compare_saved_runtime.py','workflow_io.py','workflow_cases.py','interpreter.py'])]:
            if p.is_file():bind(p)
        assert not subprocess.check_output(['git','diff','--name-only','HEAD']).strip()
        revision=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
        work=ROOT/'.work'/NAME;work.mkdir(exist_ok=False)
        write(work/'plan.json',dict(owner=str(ROOT),source_revision=revision,frozen=frozen,expected_commands=2,
            cases=cases,test=TEST,minimum_child_gib=8,performance_measurement=False,source_modified=False))
        env={k:v for k,v in os.environ.items() if not k.startswith(('RUST_INTERP_','RUSTDEV_','DYLD_')) and k!='RUST_TEST_THREADS'}
        assert not any(k.startswith('DYLD_') for k in os.environ)
        observed=[]
        for case in cases:
            require_space(ROOT,8);cmd=[case['executable'],'--exact',TEST,'--test-threads=2']
            child,out,err=capture(cmd,cwd=source,env=env,receipt_path=work/'active.json',receipt=dict(label=case['label']))
            for suffix,payload in [('stdout',out),('stderr',err)]:(work/(case['label']+'.'+suffix)).write_text(payload)
            observed.append(dict(label=case['label'],pid=child.pid,command=cmd,returncode=child.returncode,
                stdout_sha256=sha(work/(case['label']+'.stdout')),stderr_sha256=sha(work/(case['label']+'.stderr'))));write(work/'records.json',observed)
            assert child.returncode==case['expected_returncode'],(out+err)[-2500:]
            passed=case['expected_returncode']==0
            assert f'test {TEST} ... '+('ok' if passed else 'FAILED') in out
            assert f'{1 if passed else 0} passed; {0 if passed else 1} failed; 0 ignored;' in out
            assert 'running 1 test\n' in out
            assert all(sha(ROOT/p)==h for p,h in frozen.items());print(case['label'],'expected outcome confirmed',flush=True)
        result=ROOT/'results'/NAME;result.mkdir(exist_ok=False)
        write(result/'summary.json',dict(status='passed',source_revision=revision,commands=2,test=TEST,
            original_passed=True,wrong_edit_failed=True,source_modified=False,source_unchanged=True,
            raw=str(work.relative_to(ROOT)),plan_sha256=sha(work/'plan.json'),records_sha256=sha(work/'records.json'),
            original_project_native_commands=2,performance_measurement=False))
if __name__=='__main__':main()
